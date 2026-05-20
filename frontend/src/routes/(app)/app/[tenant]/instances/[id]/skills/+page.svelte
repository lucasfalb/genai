<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import Plus from '@lucide/svelte/icons/plus';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Database from '@lucide/svelte/icons/database';
	import Puzzle from '@lucide/svelte/icons/puzzle';
	import Network from '@lucide/svelte/icons/network';
	import Eye from '@lucide/svelte/icons/eye';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import ClipboardPaste from '@lucide/svelte/icons/clipboard-paste';
	import Play from '@lucide/svelte/icons/play';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import RegistryAddDialog from '$lib/components/instance/registry-add-dialog.svelte';
	import KeyValueJsonEditor from '$lib/components/registry/KeyValueJsonEditor.svelte';
	import VariableValuesEditor from '$lib/components/registry/VariableValuesEditor.svelte';
	import { registryApi } from '$lib/api/registry';
	import { instancesApi } from '$lib/api/instances';
	import { getErrorMessage } from '$lib/api/client';
	import type {
		AgentInstanceResponse,
		AgentLinkResponse,
		AgentLinkTransferMode,
		ToolMetadataResponse,
		SkillActivationResponse,
		ToolActivationResponse,
		ToolVariableSpec,
		CredentialResponse
	} from '$lib/api/types';

	let { data } = $props();

	const { register, unregister, setSaving } = getContext<{
		register: (handler: () => Promise<void>, label: string) => void;
		unregister: () => void;
		setSaving: (v: boolean) => void;
	}>('save-action');

	let registryMetadata = $state<ToolMetadataResponse>(data.registryMetadata);
	let credentials = $state<CredentialResponse[]>([]);
	let registryBusy = $state('');
	let linkBusy = $state('');
	let expandedConfig = $state('');
	let addSkillOpen = $state(false);
	let addToolOpen = $state(false);
	let addLinkOpen = $state(false);
	let credentialInputs = $state<Record<string, string>>({});
	let credentialVisible = $state<Record<string, boolean>>({});
	type HttpOverride = {
		method: string;
		endpoint: string;
		headers_template: string;
		body_template: string;
	};
	type ToolDraft = {
		prompt_block_override: string;
		variables: Record<string, string>;
		http: HttpOverride;
	};
	type SkillDraft = { prompt_block_override: string };
	type LinkDraft = {
		target_instance_id: string;
		trigger_description: string;
		transfer_mode: AgentLinkTransferMode;
		is_enabled: boolean;
	};
	type DeleteTarget =
		| { kind: 'skill'; slug: string }
		| { kind: 'tool'; slug: string }
		| { kind: 'credential'; slug: string }
		| { kind: 'link'; id: string };
	let toolDrafts = $state<Record<string, ToolDraft>>({});
	let skillDrafts = $state<Record<string, SkillDraft>>({});
	let linkDrafts = $state<Record<string, LinkDraft>>({});
	let linkedAgents = $state<AgentLinkResponse[]>([]);
	let agentInstances = $state<AgentInstanceResponse[]>([]);
	let linksLoaded = $state(false);
	let linksLoadError = $state('');
	let newLinkDraft = $state<LinkDraft>({
		target_instance_id: '',
		trigger_description: '',
		transfer_mode: 'llm_decision',
		is_enabled: true
	});
	let deleteTarget = $state<DeleteTarget | null>(null);
	let curlDialogTool = $state<ToolActivationResponse | null>(null);
	let curlCommand = $state('');
	let testDialogTool = $state<ToolActivationResponse | null>(null);
	let testArgumentsJson = $state('{}');
	let testResult = $state<Record<string, unknown> | null>(null);
	let testBusy = $state(false);

	function isHttpConfigurable(tool: ToolActivationResponse): boolean {
		return tool.executor === 'web_fetch';
	}

	function setDraftHttpJson(tool: ToolActivationResponse, field: string, value: string) {
		if (!toolDrafts[tool.slug]) initToolDraft(tool);
		if (field === 'headers_template') toolDrafts[tool.slug].http.headers_template = value;
		if (field === 'body_template') toolDrafts[tool.slug].http.body_template = value;
		toolDrafts = { ...toolDrafts };
	}

	function setDraftVariables(tool: ToolActivationResponse, values: Record<string, string>) {
		if (!toolDrafts[tool.slug]) initToolDraft(tool);
		toolDrafts[tool.slug].variables = values;
		toolDrafts = { ...toolDrafts };
	}

	function setDraftJsonError(_field: string, message: string) {
		toast.error(message);
	}

	function clearDraftJsonError(_field: string) {
		// Validation runs on save; this callback keeps the shared JSON editor contract consistent.
	}

	function openCurlDialog(tool: ToolActivationResponse) {
		initToolDraft(tool);
		curlDialogTool = tool;
		curlCommand = '';
	}

	function openTestDialog(tool: ToolActivationResponse) {
		initToolDraft(tool);
		testDialogTool = tool;
		testArgumentsJson = '{}';
		testResult = null;
	}

	async function refreshRegistryMetadata() {
		const [meta, creds] = await Promise.all([
			registryApi.getMetadata(data.instance.id),
			registryApi.getCredentials()
		]);
		registryMetadata = meta;
		credentials = creds;
	}

	async function refreshLinkedAgents() {
		linksLoadError = '';
		try {
			const [instances, links] = await Promise.all([
				instancesApi.list(),
				instancesApi.listLinks(data.instance.id)
			]);
			agentInstances = instances;
			linkedAgents = links;
			linksLoaded = true;
			const linkIds = new Set(links.map((link) => link.id));
			const nextDrafts: Record<string, LinkDraft> = {};
			for (const link of links) {
				if (linkDrafts[link.id] && linkIds.has(link.id)) nextDrafts[link.id] = linkDrafts[link.id];
			}
			linkDrafts = nextDrafts;
		} catch (err) {
			linksLoadError = getErrorMessage(err, 'Linked agents could not be loaded.');
			linksLoaded = true;
		}
	}

	function availableLinkTargets(): AgentInstanceResponse[] {
		const linkedTargetIds = new Set(linkedAgents.map((link) => link.target_instance_id));
		return agentInstances.filter(
			(instance) => instance.id !== data.instance.id && !linkedTargetIds.has(instance.id)
		);
	}

	function targetAgent(link: AgentLinkResponse): AgentInstanceResponse | undefined {
		return agentInstances.find((instance) => instance.id === link.target_instance_id);
	}

	function linkToDraft(link: AgentLinkResponse): LinkDraft {
		return {
			target_instance_id: link.target_instance_id,
			trigger_description: link.trigger_description,
			transfer_mode: link.transfer_mode,
			is_enabled: link.is_enabled
		};
	}

	function initLinkDraft(link: AgentLinkResponse) {
		if (linkDrafts[link.id]) return;
		linkDrafts[link.id] = linkToDraft(link);
		linkDrafts = { ...linkDrafts };
	}

	function resetNewLinkDraft(targetId = '') {
		const target = agentInstances.find((instance) => instance.id === targetId);
		newLinkDraft = {
			target_instance_id: targetId,
			trigger_description: target
				? `Use when the conversation should be transferred to ${target.name}.`
				: '',
			transfer_mode: 'llm_decision',
			is_enabled: true
		};
	}

	function defaultTransferToolName(name: string): string {
		const slug = name
			.toLowerCase()
			.normalize('NFKD')
			.replace(/[\u0300-\u036f]/g, '')
			.replace(/[^a-z0-9]+/g, '_')
			.replace(/^_+|_+$/g, '')
			.slice(0, 48);
		return `transfer_to_${slug || 'agent'}`;
	}

	function validateLinkDraft(draft: LinkDraft): boolean {
		if (!draft.target_instance_id) {
			toast.error('Choose a target agent.');
			return false;
		}
		if (!draft.trigger_description.trim()) {
			toast.error('Trigger instructions are required.');
			return false;
		}
		return true;
	}

	function getCredential(slug: string): CredentialResponse | undefined {
		return credentials.find((c) => c.skill_slug === slug);
	}

	function maskSecret(ref: string): string {
		if (!ref) return '';
		if (ref.length <= 4) return '****';
		return `****${ref.slice(-4)}`;
	}

	function credentialLabel(skill: SkillActivationResponse): string {
		if (skill.credential_schema?.title) return String(skill.credential_schema.title);
		return (skill.credential_schema?.label as string) ?? 'API Key';
	}

	function hasSkillConfig(skill: SkillActivationResponse): boolean {
		const cfg = skill.config ?? {};
		return Object.keys(cfg).some((k) => k !== 'prompt_block_override');
	}

	function toolVariableSpecs(tool: ToolActivationResponse): ToolVariableSpec[] {
		return (tool.variables_schema ?? []) as ToolVariableSpec[];
	}

	function initToolDraft(tool: ToolActivationResponse) {
		if (toolDrafts[tool.slug]) return;
		const cfg = (tool.config ?? {}) as Record<string, unknown>;
		const vars = (cfg.variables as Record<string, unknown>) ?? {};
		const specs = toolVariableSpecs(tool);
		const variables: Record<string, string> = {};
		for (const spec of specs) {
			const cur = vars[spec.name];
			variables[spec.name] =
				cur != null ? String(cur) : spec.default != null ? String(spec.default) : '';
		}
		const http = (cfg.http as Record<string, unknown>) ?? {};
		const httpHeaders = (http.headers as Record<string, string>) ?? tool.headers_template ?? {};
		toolDrafts[tool.slug] = {
			prompt_block_override:
				typeof cfg.prompt_block_override === 'string' ? cfg.prompt_block_override : '',
			variables,
			http: {
				method: typeof http.method === 'string' ? http.method : (tool.method ?? 'GET'),
				endpoint: typeof http.endpoint === 'string' ? http.endpoint : (tool.endpoint ?? ''),
				headers_template: JSON.stringify(httpHeaders, null, 2),
				body_template: typeof http.body === 'string' ? http.body : (tool.body_template ?? '{}')
			}
		};
		toolDrafts = { ...toolDrafts };
	}

	function initSkillDraft(skill: SkillActivationResponse) {
		if (skillDrafts[skill.slug]) return;
		const cfg = (skill.config ?? {}) as Record<string, unknown>;
		skillDrafts[skill.slug] = {
			prompt_block_override:
				typeof cfg.prompt_block_override === 'string' ? cfg.prompt_block_override : ''
		};
		skillDrafts = { ...skillDrafts };
	}

	function openConfig(key: string, skillSlug?: string) {
		if (expandedConfig !== key && skillSlug && !(skillSlug in credentialInputs)) {
			const cred = getCredential(skillSlug);
			credentialInputs[skillSlug] = cred?.secret_ref ?? '';
			credentialInputs = { ...credentialInputs };
		}
		expandedConfig = expandedConfig === key ? '' : key;
	}

	async function configureSkill(skill: SkillActivationResponse, config = skill.config ?? {}) {
		registryBusy = `skill:${skill.slug}`;
		try {
			await registryApi.activateSkill(data.instance.id, skill.slug, { is_enabled: true, config });
			await refreshRegistryMetadata();
			toast.success('Skill updated.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Skill update failed.'));
		} finally {
			registryBusy = '';
		}
	}

	async function configureTool(tool: ToolActivationResponse, config = tool.config ?? {}) {
		registryBusy = `tool:${tool.slug}`;
		try {
			await registryApi.activateToolItem(data.instance.id, tool.slug, { is_enabled: true, config });
			await refreshRegistryMetadata();
			toast.success('Tool updated.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Tool update failed.'));
		} finally {
			registryBusy = '';
		}
	}

	function requestRemoveSkill(slug: string) {
		deleteTarget = { kind: 'skill', slug };
	}

	async function removeSkill(slug: string) {
		registryBusy = `skill:${slug}`;
		try {
			await registryApi.removeSkill(data.instance.id, slug);
			await refreshRegistryMetadata();
			toast.success(`Skill "${slug}" removed.`);
		} catch (err) {
			toast.error(getErrorMessage(err, 'Remove failed.'));
		} finally {
			registryBusy = '';
		}
	}

	function requestRemoveTool(slug: string) {
		deleteTarget = { kind: 'tool', slug };
	}

	async function removeTool(slug: string) {
		registryBusy = `tool:${slug}`;
		try {
			await registryApi.removeTool(data.instance.id, slug);
			await refreshRegistryMetadata();
			toast.success(`Tool "${slug}" removed.`);
		} catch (err) {
			toast.error(getErrorMessage(err, 'Remove failed.'));
		} finally {
			registryBusy = '';
		}
	}

	async function createLink() {
		const draft = newLinkDraft;
		if (!validateLinkDraft(draft)) return;
		linkBusy = 'link:new';
		try {
			const targetAgent = agentInstances.find((i) => i.id === draft.target_instance_id);
			await instancesApi.createLink(data.instance.id, {
				target_instance_id: draft.target_instance_id,
				transfer_tool_name: defaultTransferToolName(targetAgent?.name ?? draft.target_instance_id),
				trigger_description: draft.trigger_description.trim(),
				transfer_mode: draft.transfer_mode,
				is_enabled: draft.is_enabled
			});
			await Promise.all([refreshLinkedAgents(), refreshRegistryMetadata()]);
			addLinkOpen = false;
			resetNewLinkDraft();
			toast.success('Linked agent added.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Add linked agent failed.'));
		} finally {
			linkBusy = '';
		}
	}

	function requestRemoveLink(id: string) {
		deleteTarget = { kind: 'link', id };
	}

	async function removeLink(id: string) {
		linkBusy = `link:${id}`;
		try {
			await instancesApi.deleteLink(data.instance.id, id);
			await Promise.all([refreshLinkedAgents(), refreshRegistryMetadata()]);
			toast.success('Linked agent removed.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Remove linked agent failed.'));
		} finally {
			linkBusy = '';
		}
	}

	async function addSkill(slug: string) {
		try {
			await registryApi.activateSkill(data.instance.id, slug, { is_enabled: true, config: {} });
			await refreshRegistryMetadata();
			toast.success(`Skill "${slug}" added.`);
		} catch (err) {
			toast.error(getErrorMessage(err, 'Add skill failed.'));
		}
	}

	async function addTool(slug: string) {
		try {
			await registryApi.activateToolItem(data.instance.id, slug, { is_enabled: true, config: {} });
			await refreshRegistryMetadata();
			toast.success(`Tool "${slug}" added.`);
		} catch (err) {
			toast.error(getErrorMessage(err, 'Add tool failed.'));
		}
	}

	async function saveCredential(slug: string) {
		const value = credentialInputs[slug] ?? '';
		if (!value.trim()) {
			toast.error('Credential value is required.');
			return;
		}
		registryBusy = `cred:${slug}`;
		try {
			await registryApi.saveCredential(slug, {
				secret_ref: value.trim(),
				metadata: {}
			});
			await refreshRegistryMetadata();
			credentialInputs[slug] = '';
			toast.success('Credential saved.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Failed to save credential.'));
		} finally {
			registryBusy = '';
		}
	}

	function requestDeleteCredential(slug: string) {
		deleteTarget = { kind: 'credential', slug };
	}

	async function deleteCredential(slug: string) {
		registryBusy = `cred:${slug}`;
		try {
			await registryApi.saveCredential(slug, { secret_ref: '', metadata: {} });
			await refreshRegistryMetadata();
			toast.success('Credential removed.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Failed to remove credential.'));
		} finally {
			registryBusy = '';
		}
	}

	async function confirmDeleteTarget() {
		if (!deleteTarget) return;
		const target = deleteTarget;
		deleteTarget = null;
		if (target.kind === 'skill') {
			await removeSkill(target.slug);
			return;
		}
		if (target.kind === 'tool') {
			await removeTool(target.slug);
			return;
		}
		if (target.kind === 'link') {
			await removeLink(target.id);
			return;
		}
		await deleteCredential(target.slug);
	}

	function deleteTitle(target: DeleteTarget | null): string {
		if (target?.kind === 'tool') return 'Delete Tool';
		if (target?.kind === 'skill') return 'Delete Skill';
		if (target?.kind === 'link') return 'Delete Linked Agent';
		return 'Delete Credential';
	}

	function deleteDescription(target: DeleteTarget | null): string {
		if (!target) return '';
		if (target.kind === 'link') {
			const link = linkedAgents.find((item) => item.id === target.id);
			const targetName = link ? (link.target_name ?? link.target_instance_id) : 'this agent';
			return `Remove the handoff tool for "${targetName}" from this instance?`;
		}
		if (target.kind === 'credential') {
			return `Delete credential for "${target.slug}"? Requests using this credential may stop working until a new value is saved.`;
		}
		return `Delete "${target.slug}" from this agent instance? This does not delete the global registry definition.`;
	}

	function tokenizeCurl(command: string): string[] {
		const tokens: string[] = [];
		let current = '';
		let quote: '"' | "'" | '' = '';
		let escaping = false;
		for (const char of command.replace(/\\\r?\n/g, ' ')) {
			if (escaping) {
				current += char;
				escaping = false;
				continue;
			}
			if (char === '\\' && quote !== "'") {
				escaping = true;
				continue;
			}
			if ((char === '"' || char === "'") && (!quote || quote === char)) {
				quote = quote ? '' : char;
				continue;
			}
			if (/\s/.test(char) && !quote) {
				if (current) tokens.push(current);
				current = '';
				continue;
			}
			current += char;
		}
		if (current) tokens.push(current);
		return tokens;
	}

	function importCurl() {
		if (!curlDialogTool) return;
		const tokens = tokenizeCurl(curlCommand.trim());
		if (!tokens.length || tokens[0] !== 'curl') {
			toast.error('Paste a valid curl command.');
			return;
		}
		const headers: Record<string, string> = {};
		let method = '';
		let endpoint = '';
		let body = '';
		for (let i = 1; i < tokens.length; i += 1) {
			const token = tokens[i];
			const next = tokens[i + 1];
			if (token === '-X' || token === '--request') {
				method = (next ?? '').toUpperCase();
				i += 1;
				continue;
			}
			if (token === '-H' || token === '--header') {
				const [name, ...rest] = (next ?? '').split(':');
				if (name && rest.length) headers[name.trim()] = rest.join(':').trim();
				i += 1;
				continue;
			}
			if (['-d', '--data', '--data-raw', '--data-binary', '--json'].includes(token)) {
				body = next ?? '';
				if (!method) method = 'POST';
				i += 1;
				continue;
			}
			if (!token.startsWith('-') && !endpoint) endpoint = token;
		}
		if (!endpoint) {
			toast.error('Could not find a URL in the curl command.');
			return;
		}
		if (!['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
			method = body ? 'POST' : 'GET';
		}
		if (!toolDrafts[curlDialogTool.slug]) initToolDraft(curlDialogTool);
		toolDrafts[curlDialogTool.slug].http = {
			method: method || 'GET',
			endpoint,
			headers_template: JSON.stringify(headers, null, 2),
			body_template: body || '{}'
		};
		toolDrafts = { ...toolDrafts };
		curlDialogTool = null;
		curlCommand = '';
		toast.success('cURL imported.');
	}

	function buildToolConfig(
		tool: ToolActivationResponse,
		draft: ToolDraft
	): Record<string, unknown> | null {
		const baseConfig = (tool.config ?? {}) as Record<string, unknown>;
		const variables: Record<string, string> = {};
		for (const [key, value] of Object.entries(draft.variables)) {
			if (value !== '') variables[key] = value;
		}
		const config: Record<string, unknown> = { ...baseConfig };
		if (Object.keys(variables).length > 0) config.variables = variables;
		else delete config.variables;
		const override = draft.prompt_block_override.trim();
		if (override && override !== tool.prompt_block.trim()) config.prompt_block_override = override;
		else delete config.prompt_block_override;

		if (isHttpConfigurable(tool)) {
			if (!draft.http.endpoint.trim()) {
				toast.error('Endpoint is required for web_fetch.');
				return null;
			}
			let headers: Record<string, string> = {};
			if (draft.http.headers_template.trim()) {
				try {
					const parsed = JSON.parse(draft.http.headers_template);
					if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
						for (const [key, value] of Object.entries(parsed)) headers[key] = String(value);
					} else {
						toast.error('Headers template must be a JSON object.');
						return null;
					}
				} catch {
					toast.error('Headers template JSON is invalid.');
					return null;
				}
			}
			if (draft.http.body_template.trim()) {
				try {
					JSON.parse(draft.http.body_template);
				} catch {
					toast.error('Body template JSON is invalid.');
					return null;
				}
			}
			const http: Record<string, unknown> = {
				method: draft.http.method,
				endpoint: draft.http.endpoint.trim(),
				headers
			};
			if (draft.http.body_template.trim()) http.body = draft.http.body_template;
			config.http = http;
		}
		return config;
	}

	async function runToolTest() {
		if (!testDialogTool) return;
		const draft = toolDrafts[testDialogTool.slug];
		if (!draft) {
			toast.info('Open the tool config before testing.');
			return;
		}
		const config = buildToolConfig(testDialogTool, draft);
		if (!config) return;
		let args: Record<string, unknown> = {};
		try {
			const parsed = JSON.parse(testArgumentsJson || '{}');
			if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) args = parsed;
			else {
				toast.error('Test arguments must be a JSON object.');
				return;
			}
		} catch {
			toast.error('Test arguments JSON is invalid.');
			return;
		}
		testBusy = true;
		try {
			const result = await registryApi.testTool(data.instance.id, testDialogTool.slug, {
				config,
				arguments: args
			});
			testResult = result.raw;
			if (result.error) toast.error(result.error);
			else toast.success('Tool test completed.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Tool test failed.'));
		} finally {
			testBusy = false;
		}
	}

	function toggleCredentialVisibility(slug: string) {
		credentialVisible[slug] = !credentialVisible[slug];
		credentialVisible = { ...credentialVisible };
	}

	async function saveToolDraft(tool: ToolActivationResponse) {
		const draft = toolDrafts[tool.slug];
		if (!draft) {
			toast.info('Open the tool config before saving changes.');
			return;
		}
		const config = buildToolConfig(tool, draft);
		if (!config) return;

		registryBusy = `tool:${tool.slug}`;
		try {
			await registryApi.activateToolItem(data.instance.id, tool.slug, {
				is_enabled: true,
				config
			});
			await refreshRegistryMetadata();
			toast.success('Tool configuration saved.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Tool update failed.'));
		} finally {
			registryBusy = '';
		}
	}

	async function saveSkillDraft(skill: SkillActivationResponse) {
		const draft = skillDrafts[skill.slug];
		if (!draft) {
			toast.info('Open the skill config before saving changes.');
			return;
		}
		const baseConfig = (skill.config ?? {}) as Record<string, unknown>;
		const config: Record<string, unknown> = { ...baseConfig };
		const override = draft.prompt_block_override.trim();
		if (override && override !== skill.prompt_block.trim()) config.prompt_block_override = override;
		else delete config.prompt_block_override;

		registryBusy = `skill:${skill.slug}`;
		try {
			await registryApi.activateSkill(data.instance.id, skill.slug, {
				is_enabled: true,
				config
			});
			await refreshRegistryMetadata();
			toast.success('Skill configuration saved.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Skill update failed.'));
		} finally {
			registryBusy = '';
		}
	}

	async function saveLinkDraft(link: AgentLinkResponse) {
		const draft = linkDrafts[link.id];
		if (!draft) {
			toast.info('Open the linked agent config before saving changes.');
			return;
		}
		if (!validateLinkDraft(draft)) return;

		linkBusy = `link:${link.id}`;
		try {
			await instancesApi.updateLink(data.instance.id, link.id, {
				trigger_description: draft.trigger_description.trim(),
				transfer_mode: draft.transfer_mode,
				is_enabled: draft.is_enabled
			});
			await Promise.all([refreshLinkedAgents(), refreshRegistryMetadata()]);
			toast.success('Linked agent saved.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Linked agent update failed.'));
		} finally {
			linkBusy = '';
		}
	}

	async function saveAllDrafts() {
		setSaving(true);
		try {
			let saved = 0;
			for (const skill of registryMetadata.skills) {
				if (skillDrafts[skill.slug]) {
					await saveSkillDraft(skill);
					saved += 1;
				}
				const credential = credentialInputs[skill.slug];
				if (credential?.trim()) {
					await saveCredential(skill.slug);
					saved += 1;
				}
			}
			for (const tool of registryMetadata.tools) {
				if (toolDrafts[tool.slug]) {
					await saveToolDraft(tool);
					saved += 1;
				}
			}
			for (const link of linkedAgents) {
				if (linkDrafts[link.id]) {
					await saveLinkDraft(link);
					saved += 1;
				}
			}
			if (saved === 0) toast.info('No tool changes to save.');
		} finally {
			setSaving(false);
		}
	}

	onMount(() => {
		refreshLinkedAgents();
		register(saveAllDrafts, 'Save changes');
		return () => unregister();
	});
</script>

<div class="mx-auto space-y-6 px-6 py-5">
	<!-- Skills -->
	<section class="p-6" style="background:var(--surface);border:1px solid var(--ds-border)">
		<div class="mb-4 flex items-center justify-between">
			<div>
				<h3 class="font-display text-sm font-semibold" style="color:var(--text-main)">Skills</h3>
				<p class="mt-0.5 text-xs text-muted-foreground">
					Instance-level skill activation and configuration
				</p>
			</div>
			<Button variant="outline" size="sm" onclick={() => (addSkillOpen = true)}>
				<Plus data-icon="inline-start" />
				Add Skill
			</Button>
		</div>

		{#if registryMetadata.skills.length === 0}
			<p class="py-6 text-center text-sm text-muted-foreground">
				No skills yet. Click "Add Skill" to pick from the catalog.
			</p>
		{:else}
			<div class="space-y-3">
				{#each registryMetadata.skills as skill (skill.slug)}
					{@const key = `skill:${skill.slug}`}
					{@const busy = registryBusy === key}
					{@const expanded = expandedConfig === key}
					{@const cred = getCredential(skill.slug)}
					<div
						class="rounded-lg p-4"
						style="background:var(--surface-hover);border:1px solid var(--ds-border)"
					>
						<div class="flex flex-wrap items-start justify-between gap-3">
							<div class="min-w-0 flex-1">
								<div class="flex items-center gap-2">
									<div
										class="flex size-8 items-center justify-center rounded-md bg-blue-500/10 text-blue-400"
									>
										<Puzzle class="size-4" />
									</div>
									<div>
										<p class="text-sm font-semibold" style="color:var(--text-main)">{skill.name}</p>
										<p class="text-xs text-muted-foreground/70">{skill.slug}</p>
									</div>
								</div>
								{#if skill.description}
									<p class="mt-2 text-xs text-muted-foreground">{skill.description}</p>
								{/if}
								<div class="mt-2 flex flex-wrap gap-2">
									<Badge variant="outline" class="text-[10px]"
										>{skill.category ?? 'uncategorized'}</Badge
									>
									<Badge variant="outline" class="font-mono text-[10px]">{skill.executor}</Badge>
									{#if skill.requires_credential}
										<Badge variant="outline" class="border-amber-400/30 text-[10px] text-amber-400"
											>requires credential</Badge
										>
									{/if}
								</div>
							</div>
							<div class="flex shrink-0 items-center gap-2">
								<Button
									variant="ghost"
									size="sm"
									onclick={() => {
										initSkillDraft(skill);
										openConfig(key, skill.slug);
									}}
								>
									Config
								</Button>
								<Button
									variant="destructive"
									size="sm"
									disabled={busy}
									onclick={() => requestRemoveSkill(skill.slug)}
									title="Remove skill"
								>
									{#if busy}<Spinner data-icon="inline-start" />{/if}
									<Trash2 class="size-3.5" />
								</Button>
							</div>
						</div>
						{#if expanded}
							<div
								class="mt-4 space-y-4 rounded-lg border bg-[var(--canvas)] p-4 text-sm text-muted-foreground"
								style="border-color:var(--ds-border)"
							>
								{#if hasSkillConfig(skill)}
									<div>
										<p
											class="mb-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase"
										>
											Configuration
										</p>
										{#each Object.entries(skill.config!).filter(([k]) => k !== 'prompt_block_override') as [key, value]}
											<div class="mb-2 grid grid-cols-[140px_1fr] gap-2 text-xs">
												<span class="font-mono text-foreground/70">{key}</span>
												<span class="text-foreground/80"
													>{typeof value === 'string' ? value : JSON.stringify(value)}</span
												>
											</div>
										{/each}
									</div>
								{/if}
								<div>
									<p
										class="mb-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase"
									>
										Instruction
									</p>
									<textarea
										rows="3"
										value={skillDrafts[skill.slug]?.prompt_block_override || skill.prompt_block}
										oninput={(e) => {
											if (!skillDrafts[skill.slug])
												skillDrafts[skill.slug] = { prompt_block_override: '' };
											skillDrafts[skill.slug].prompt_block_override = e.currentTarget.value;
											skillDrafts = { ...skillDrafts };
										}}
										class="auth-input w-full rounded-lg px-3.5 py-2.5 text-sm"
									></textarea>
									<div class="mt-2 flex justify-end">
										<Button
											variant="default"
											size="sm"
											disabled={registryBusy === `skill:${skill.slug}`}
											onclick={() => saveSkillDraft(skill)}
										>
											{#if registryBusy === `skill:${skill.slug}`}<Spinner
													data-icon="inline-start"
												/>{/if}
											Save instruction
										</Button>
									</div>
								</div>
								{#if skill.requires_credential}
									<div>
										<p
											class="mb-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase"
										>
											{credentialLabel(skill)}
										</p>
										<div class="flex items-center gap-2">
											<div class="relative flex-1">
												<input
													type={credentialVisible[skill.slug] ? 'text' : 'password'}
													placeholder={cred ? '********' : 'Insert the credential value'}
													value={credentialInputs[skill.slug] ?? ''}
													oninput={(e) => {
														credentialInputs[skill.slug] = e.currentTarget.value;
														credentialInputs = { ...credentialInputs };
													}}
													class="auth-input w-full rounded-lg px-3.5 py-2.5 pr-10 font-mono text-sm"
												/>
												<button
													onclick={() => toggleCredentialVisibility(skill.slug)}
													class="absolute top-1/2 right-2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
													title={credentialVisible[skill.slug] ? 'Hide' : 'Show'}
												>
													{#if credentialVisible[skill.slug]}
														<EyeOff class="size-4" />
													{:else}
														<Eye class="size-4" />
													{/if}
												</button>
											</div>
											<Button
												variant="default"
												size="sm"
												disabled={registryBusy === `cred:${skill.slug}` ||
													!(credentialInputs[skill.slug] ?? '').trim()}
												onclick={() => saveCredential(skill.slug)}
											>
												{#if registryBusy === `cred:${skill.slug}`}<Spinner
														data-icon="inline-start"
													/>{/if}
												Save
											</Button>
											{#if cred}
												<Button
													variant="destructive"
													size="sm"
													disabled={registryBusy === `cred:${skill.slug}`}
													onclick={() => requestDeleteCredential(skill.slug)}
													title="Remove credential"
												>
													<Trash2 class="size-3.5" />
												</Button>
											{/if}
										</div>
									</div>
								{/if}
							</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</section>

	<!-- Tools -->
	<section class="p-6" style="background:var(--surface);border:1px solid var(--ds-border)">
		<div class="mb-4 flex items-center justify-between">
			<div>
				<h3 class="font-display text-sm font-semibold" style="color:var(--text-main)">Tools</h3>
				<p class="mt-0.5 text-xs text-muted-foreground">
					Utility tools available to this agent instance
				</p>
			</div>
			<Button variant="outline" size="sm" onclick={() => (addToolOpen = true)}>
				<Plus data-icon="inline-start" />
				Add Tool
			</Button>
		</div>

		{#if registryMetadata.tools.length === 0}
			<p class="py-6 text-center text-sm text-muted-foreground">
				No tools yet. Click "Add Tool" to pick from the catalog.
			</p>
		{:else}
			<div class="space-y-3">
				{#each registryMetadata.tools as tool (tool.slug)}
					{@const key = `tool:${tool.slug}`}
					{@const busy = registryBusy === key}
					{@const expanded = expandedConfig === key}
					{@const variableSpecs = toolVariableSpecs(tool)}
					<div
						class="rounded-lg p-4"
						style="background:var(--surface-hover);border:1px solid var(--ds-border)"
					>
						<div class="flex flex-wrap items-start justify-between gap-3">
							<div class="min-w-0 flex-1">
								<div class="flex items-center gap-2">
									<div
										class="flex size-8 items-center justify-center rounded-md bg-blue-500/10 text-blue-400"
									>
										<Database class="size-4" />
									</div>
									<div>
										<p class="text-sm font-semibold" style="color:var(--text-main)">{tool.name}</p>
										<p class="text-xs text-muted-foreground/70">{tool.slug}</p>
									</div>
								</div>
								{#if tool.description}
									<p class="mt-2 text-xs text-muted-foreground">{tool.description}</p>
								{/if}
								<div class="mt-2 flex flex-wrap gap-2">
									<Badge variant="outline" class="text-[10px]"
										>{tool.category ?? 'uncategorized'}</Badge
									>
									<Badge variant="outline" class="font-mono text-[10px]">{tool.executor}</Badge>
									{#if tool.is_builtin}
										<Badge
											variant="outline"
											class="border-emerald-400/30 text-[10px] text-emerald-400">builtin</Badge
										>
									{/if}
								</div>
							</div>
							<div class="flex shrink-0 items-center gap-2">
								<Button
									variant="ghost"
									size="sm"
									onclick={() => {
										initToolDraft(tool);
										openConfig(key);
									}}
								>
									Config
								</Button>
								<Button
									variant="destructive"
									size="sm"
									disabled={busy}
									onclick={() => requestRemoveTool(tool.slug)}
									title="Remove tool"
								>
									{#if busy}<Spinner data-icon="inline-start" />{/if}
									<Trash2 class="size-3.5" />
								</Button>
							</div>
						</div>
						{#if expanded}
							<div
								class="mt-4 space-y-4 rounded-lg border bg-[var(--canvas)] p-4 text-sm text-muted-foreground"
								style="border-color:var(--ds-border)"
							>
								<div>
									<p
										class="mb-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase"
									>
										Instruction
									</p>
									<textarea
										rows="3"
										value={toolDrafts[tool.slug]?.prompt_block_override || tool.prompt_block}
										oninput={(e) => {
											if (!toolDrafts[tool.slug]) initToolDraft(tool);
											toolDrafts[tool.slug].prompt_block_override = e.currentTarget.value;
											toolDrafts = { ...toolDrafts };
										}}
										class="auth-input w-full rounded-lg px-3.5 py-2.5 text-sm"
									></textarea>
								</div>
								{#if isHttpConfigurable(tool)}
									<div>
										<div class="mb-2 flex flex-wrap items-center justify-between gap-2">
											<p
												class="text-[11px] font-semibold tracking-wider text-muted-foreground uppercase"
											>
												HTTP Request
											</p>
											<div class="flex items-center gap-2">
												<Button variant="outline" size="sm" onclick={() => openCurlDialog(tool)}>
													<ClipboardPaste data-icon="inline-start" />
													Import cURL
												</Button>
												<Button variant="outline" size="sm" onclick={() => openTestDialog(tool)}>
													<Play data-icon="inline-start" />
													Test
												</Button>
											</div>
										</div>
										<p class="mb-3 text-[11px] text-muted-foreground/70">
											Configure this instance override. Use <span class="font-mono">{'{var}'}</span> placeholders
											from AI tool-call arguments or variables filled below.
										</p>
										<div class="space-y-3">
											<div class="grid grid-cols-[120px_1fr] items-center gap-3">
												<label class="text-xs font-medium text-foreground/80">Method</label>
												<Select.Root
													type="single"
													value={toolDrafts[tool.slug]?.http.method ?? 'GET'}
													onValueChange={(value) => {
														if (!toolDrafts[tool.slug]) initToolDraft(tool);
														toolDrafts[tool.slug].http.method = value;
														toolDrafts = { ...toolDrafts };
													}}
												>
													<Select.Trigger class="h-9 w-full bg-background font-mono text-xs">
														{toolDrafts[tool.slug]?.http.method ?? 'GET'}
													</Select.Trigger>
													<Select.Content>
														{#each ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'] as method}
															<Select.Item value={method} label={method}>{method}</Select.Item>
														{/each}
													</Select.Content>
												</Select.Root>
											</div>
											<div>
												<label class="mb-1 block text-xs font-medium text-foreground/80"
													>Endpoint <span class="text-red-400">*</span></label
												>
												<input
													type="text"
													value={toolDrafts[tool.slug]?.http.endpoint ?? ''}
													oninput={(e) => {
														if (!toolDrafts[tool.slug]) initToolDraft(tool);
														toolDrafts[tool.slug].http.endpoint = e.currentTarget.value;
														toolDrafts = { ...toolDrafts };
													}}
													class="auth-input w-full rounded-lg px-3.5 py-2.5 font-mono text-sm"
												/>
											</div>
											<KeyValueJsonEditor
												field="headers_template"
												value={toolDrafts[tool.slug]?.http.headers_template ?? '{}'}
												label="Headers template"
												description={'Request headers for this instance. Use placeholders such as {api_key} or {query}.'}
												keyPlaceholder=""
												valuePlaceholder={''}
												resetKey={`${tool.slug}:${expandedConfig}`}
												onValueChange={(_field, value) =>
													setDraftHttpJson(tool, 'headers_template', value)}
												onError={setDraftJsonError}
												onClear={clearDraftJsonError}
											/>
											<KeyValueJsonEditor
												field="body_template"
												value={toolDrafts[tool.slug]?.http.body_template ?? '{}'}
												label="Body template"
												description="JSON body sent for POST, PUT, or PATCH. Values can use placeholders."
												keyPlaceholder=""
												valuePlaceholder={''}
												resetKey={`${tool.slug}:${expandedConfig}`}
												onValueChange={(_field, value) =>
													setDraftHttpJson(tool, 'body_template', value)}
												onError={setDraftJsonError}
												onClear={clearDraftJsonError}
											/>
										</div>
									</div>
								{:else if tool.endpoint}
									<div>
										<p
											class="mb-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase"
										>
											HTTP Request
										</p>
										<div class="grid grid-cols-[80px_1fr] gap-2 text-xs">
											<span class="font-mono text-foreground/70">method</span>
											<span class="font-mono text-foreground/80">{tool.method ?? 'GET'}</span>
											<span class="font-mono text-foreground/70">endpoint</span>
											<span class="font-mono break-all text-foreground/80">{tool.endpoint}</span>
											{#if tool.headers_template && Object.keys(tool.headers_template).length > 0}
												<span class="font-mono text-foreground/70">headers</span>
												<span class="font-mono break-all text-foreground/80"
													>{JSON.stringify(tool.headers_template)}</span
												>
											{/if}
											{#if tool.body_template}
												<span class="font-mono text-foreground/70">body</span>
												<span class="font-mono break-all text-foreground/80"
													>{tool.body_template}</span
												>
											{/if}
										</div>
									</div>
								{/if}
								{#if variableSpecs.length > 0}
									<VariableValuesEditor
										specs={variableSpecs}
										values={toolDrafts[tool.slug]?.variables ?? {}}
										resetKey={`${tool.slug}:${expandedConfig}:variables`}
										onValuesChange={(values) => setDraftVariables(tool, values)}
									/>
								{/if}
								<div class="flex justify-end">
									<Button
										variant="default"
										size="sm"
										disabled={registryBusy === `tool:${tool.slug}`}
										onclick={() => saveToolDraft(tool)}
									>
										{#if registryBusy === `tool:${tool.slug}`}<Spinner
												data-icon="inline-start"
											/>{/if}
										Save configuration
									</Button>
								</div>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</section>

	<!-- Linked agents -->
	<section class="p-6" style="background:var(--surface);border:1px solid var(--ds-border)">
		<div class="mb-4 flex items-center justify-between">
			<div>
				<h3 class="font-display text-sm font-semibold" style="color:var(--text-main)">
					Linked agents
				</h3>
				<p class="mt-0.5 text-xs text-muted-foreground">
					Handoff tools this agent can call to transfer conversations
				</p>
			</div>
			<Button
				variant="outline"
				size="sm"
				onclick={() => {
					resetNewLinkDraft(availableLinkTargets()[0]?.id ?? '');
					addLinkOpen = true;
				}}
				disabled={!linksLoaded || availableLinkTargets().length === 0}
			>
				<Plus data-icon="inline-start" />
				Add Agent
			</Button>
		</div>

		{#if linksLoadError}
			<p class="py-6 text-center text-sm text-red-400">{linksLoadError}</p>
		{:else if !linksLoaded}
			<div class="flex items-center justify-center gap-2 py-6 text-sm text-muted-foreground">
				<Spinner class="size-4" />
				Loading linked agents...
			</div>
		{:else if linkedAgents.length === 0}
			<p class="py-6 text-center text-sm text-muted-foreground">
				No linked agents yet. Add an agent to expose it as a handoff tool.
			</p>
		{:else}
			<div class="space-y-3">
				{#each linkedAgents as link (link.id)}
					{@const key = `link:${link.id}`}
					{@const busy = linkBusy === key}
					{@const expanded = expandedConfig === key}
					{@const target = targetAgent(link)}
					{@const draft = linkDrafts[link.id] ?? linkToDraft(link)}
					<div
						class="rounded-lg p-4"
						style="background:var(--surface-hover);border:1px solid var(--ds-border)"
					>
						<div class="flex flex-wrap items-start justify-between gap-3">
							<div class="min-w-0 flex-1">
								<div class="flex items-center gap-2">
									<div
										class="flex size-8 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-400"
									>
										<Network class="size-4" />
									</div>
									<div>
										<p class="text-sm font-semibold" style="color:var(--text-main)">
											{link.target_name}
										</p>
										<p class="font-mono text-xs text-muted-foreground/70">
											{link.transfer_tool_name}
										</p>
									</div>
								</div>
								<p class="mt-2 text-xs text-muted-foreground">{link.trigger_description}</p>
								<div class="mt-2 flex flex-wrap gap-2">
									<Badge variant="outline" class="font-mono text-[10px]">{link.transfer_mode}</Badge
									>
									<Badge
										variant="outline"
										class={link.is_enabled
											? 'border-emerald-400/30 text-[10px] text-emerald-400'
											: 'border-muted-foreground/30 text-[10px] text-muted-foreground'}
									>
										{link.is_enabled ? 'enabled' : 'disabled'}
									</Badge>
									{#if target?.status}
										<Badge variant="outline" class="text-[10px]">{target.status}</Badge>
									{/if}
								</div>
							</div>
							<div class="flex shrink-0 items-center gap-2">
								<Button
									variant="ghost"
									size="sm"
									onclick={() => {
										initLinkDraft(link);
										openConfig(key);
									}}
								>
									Config
								</Button>
								<Button
									variant="destructive"
									size="sm"
									disabled={busy}
									onclick={() => requestRemoveLink(link.id)}
									title="Remove linked agent"
								>
									{#if busy}<Spinner data-icon="inline-start" />{/if}
									<Trash2 class="size-3.5" />
								</Button>
							</div>
						</div>
						{#if expanded}
							<div
								class="mt-4 space-y-4 rounded-lg border bg-[var(--canvas)] p-4 text-sm text-muted-foreground"
								style="border-color:var(--ds-border)"
							>
								<div>
									<label class="mb-1 block text-xs font-medium text-foreground/80">Mode</label>
									<Select.Root
										type="single"
										value={draft.transfer_mode}
										onValueChange={(value) => {
											initLinkDraft(link);
											linkDrafts[link.id].transfer_mode = value as AgentLinkTransferMode;
											linkDrafts = { ...linkDrafts };
										}}
									>
										<Select.Trigger class="h-10 w-45 bg-background font-mono text-xs">
											{draft.transfer_mode}
										</Select.Trigger>
										<Select.Content>
											<Select.Item value="llm_decision" label="llm_decision"
												>llm_decision</Select.Item
											>
											<Select.Item value="router_classifier" label="router_classifier"
												>router_classifier</Select.Item
											>
										</Select.Content>
									</Select.Root>
								</div>
								<div>
									<label class="mb-1 block text-xs font-medium text-foreground/80">
										{draft.transfer_mode === 'router_classifier'
											? 'Classification topic'
											: 'Trigger instructions'}
										<span class="text-red-400">*</span>
									</label>
									<Textarea
										rows={4}
										placeholder={draft.transfer_mode === 'router_classifier'
											? 'e.g. billing and payment questions, subscription management'
											: 'e.g. Use this agent when the user asks about billing or payments.'}
										value={draft.trigger_description}
										oninput={(e) => {
											initLinkDraft(link);
											linkDrafts[link.id].trigger_description = e.currentTarget.value;
											linkDrafts = { ...linkDrafts };
										}}
										class="text-sm"
									/>
									{#if draft.transfer_mode === 'router_classifier'}
										<p class="mt-1 text-[11px] text-muted-foreground">
											Describe the topic or intent that routes to this agent. Keep it concise —
											the classifier matches user messages against this condition.
										</p>
									{/if}
								</div>
								<div class="flex flex-wrap items-center justify-between gap-3">
									<label class="flex items-center gap-2 text-xs text-foreground/80">
										<Switch
											checked={draft.is_enabled}
											onCheckedChange={(checked) => {
												initLinkDraft(link);
												linkDrafts[link.id].is_enabled = checked;
												linkDrafts = { ...linkDrafts };
											}}
										/>
										Enabled as handoff tool
									</label>
									<Button
										variant="default"
										size="sm"
										disabled={busy}
										onclick={() => saveLinkDraft(link)}
									>
										{#if busy}<Spinner data-icon="inline-start" />{/if}
										Save linked agent
									</Button>
								</div>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</section>
</div>

<RegistryAddDialog
	bind:open={addSkillOpen}
	kind="skill"
	excludeSlugs={registryMetadata.skills.map((s) => s.slug)}
	onPick={addSkill}
/>

<RegistryAddDialog
	bind:open={addToolOpen}
	kind="tool"
	excludeSlugs={registryMetadata.tools.map((t) => t.slug)}
	onPick={addTool}
/>

<Dialog.Root bind:open={addLinkOpen}>
	<Dialog.Content class="sm:max-w-2xl">
		<Dialog.Header>
			<Dialog.Title>Add linked agent</Dialog.Title>
			<Dialog.Description>
				Expose another tenant agent as a handoff tool for this instance.
			</Dialog.Description>
		</Dialog.Header>
		<div class="space-y-4">
			<div>
				<label class="mb-1 block text-xs font-medium text-foreground/80"
					>Target agent <span class="text-red-400">*</span></label
				>
				<Select.Root
					type="single"
					value={newLinkDraft.target_instance_id}
					onValueChange={(value) => resetNewLinkDraft(value)}
				>
					<Select.Trigger class="h-10 w-full bg-background text-sm">
						{agentInstances.find((instance) => instance.id === newLinkDraft.target_instance_id)
							?.name ?? 'Choose an agent'}
					</Select.Trigger>
					<Select.Content>
						{#each availableLinkTargets() as instance (instance.id)}
							<Select.Item value={instance.id} label={instance.name}>{instance.name}</Select.Item>
						{/each}
					</Select.Content>
				</Select.Root>
			</div>
			<div>
				<label class="mb-1 block text-xs font-medium text-foreground/80">Mode</label>
				<Select.Root
					type="single"
					value={newLinkDraft.transfer_mode}
					onValueChange={(value) => {
						newLinkDraft.transfer_mode = value as AgentLinkTransferMode;
					}}
				>
					<Select.Trigger class="h-10 w-45 bg-background font-mono text-xs">
						{newLinkDraft.transfer_mode}
					</Select.Trigger>
					<Select.Content>
						<Select.Item value="llm_decision" label="llm_decision">llm_decision</Select.Item>
						<Select.Item value="router_classifier" label="router_classifier"
							>router_classifier</Select.Item
						>
					</Select.Content>
				</Select.Root>
			</div>
			<div>
				<label class="mb-1 block text-xs font-medium text-foreground/80">
					{newLinkDraft.transfer_mode === 'router_classifier'
						? 'Classification topic'
						: 'Trigger instructions'}
					<span class="text-red-400">*</span>
				</label>
				<Textarea
					bind:value={newLinkDraft.trigger_description}
					rows={4}
					placeholder={newLinkDraft.transfer_mode === 'router_classifier'
						? 'e.g. billing and payment questions, subscription management'
						: 'e.g. Use this agent when the user asks about billing or payments.'}
					class="text-sm"
				/>
				{#if newLinkDraft.transfer_mode === 'router_classifier'}
					<p class="mt-1 text-[11px] text-muted-foreground">
						Describe the topic or intent that routes to this agent. Keep it concise — the
						classifier matches user messages against this condition.
					</p>
				{/if}
			</div>
			<label class="flex items-center gap-2 text-xs text-foreground/80">
				<Switch bind:checked={newLinkDraft.is_enabled} />
				Enabled as handoff tool
			</label>
		</div>
		<Dialog.Footer>
			<Button variant="outline" onclick={() => (addLinkOpen = false)}>Cancel</Button>
			<Button disabled={linkBusy === 'link:new'} onclick={createLink}>
				{#if linkBusy === 'link:new'}<Spinner data-icon="inline-start" />{/if}
				Add linked agent
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<Dialog.Root
	open={!!curlDialogTool}
	onOpenChange={(open) => {
		if (!open) curlDialogTool = null;
	}}
>
	<Dialog.Content class="sm:max-w-2xl">
		<Dialog.Header>
			<Dialog.Title>Import cURL</Dialog.Title>
			<Dialog.Description>
				Paste a cURL command to fill method, endpoint, headers, and body for this web_fetch tool.
			</Dialog.Description>
		</Dialog.Header>
		<Textarea bind:value={curlCommand} rows={10} class="font-mono text-xs" />
		<Dialog.Footer>
			<Button variant="outline" onclick={() => (curlDialogTool = null)}>Cancel</Button>
			<Button onclick={importCurl}>Import</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<Dialog.Root
	open={!!testDialogTool}
	onOpenChange={(open) => {
		if (!open) testDialogTool = null;
	}}
>
	<Dialog.Content class="sm:max-w-2xl">
		<Dialog.Header>
			<Dialog.Title>Test {testDialogTool?.name ?? 'tool'}</Dialog.Title>
			<Dialog.Description>
				Run the current unsaved configuration through the backend executor. Optional arguments can
				fill placeholders.
			</Dialog.Description>
		</Dialog.Header>
		<div class="space-y-3">
			<div>
				<p class="mb-1 text-xs font-medium text-foreground/80">Arguments JSON</p>
				<Textarea bind:value={testArgumentsJson} rows={5} class="font-mono text-xs" />
			</div>
			{#if testResult}
				<div>
					<p class="mb-1 text-xs font-medium text-foreground/80">Result</p>
					<pre
						class="max-h-72 overflow-auto rounded-lg border bg-background p-3 text-xs text-foreground">{JSON.stringify(
							testResult,
							null,
							2
						)}</pre>
				</div>
			{/if}
		</div>
		<Dialog.Footer>
			<Button variant="outline" onclick={() => (testDialogTool = null)}>Close</Button>
			<Button disabled={testBusy} onclick={runToolTest}>
				{#if testBusy}<Spinner data-icon="inline-start" />{/if}
				Run test
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<AlertDialog.Root
	open={!!deleteTarget}
	onOpenChange={(open) => {
		if (!open) deleteTarget = null;
	}}
>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>{deleteTitle(deleteTarget)}</AlertDialog.Title>
			<AlertDialog.Description>{deleteDescription(deleteTarget)}</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>Cancel</AlertDialog.Cancel>
			<AlertDialog.Action onclick={confirmDeleteTarget}>Delete</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
