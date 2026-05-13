<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import Plus from '@lucide/svelte/icons/plus';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Database from '@lucide/svelte/icons/database';
	import Puzzle from '@lucide/svelte/icons/puzzle';
	import Eye from '@lucide/svelte/icons/eye';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import RegistryAddDialog from '$lib/components/instance/registry-add-dialog.svelte';
	import { registryApi } from '$lib/api/registry';
	import { getErrorMessage } from '$lib/api/client';
	import type {
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
	let expandedConfig = $state('');
	let addSkillOpen = $state(false);
	let addToolOpen = $state(false);
	let credentialInputs = $state<Record<string, string>>({});
	let credentialVisible = $state<Record<string, boolean>>({});
	type HttpOverride = { method: string; endpoint: string; authorization: string; headers_extra: string; body: string };
	type ToolDraft = {
		prompt_block_override: string;
		variables: Record<string, string>;
		http: HttpOverride;
	};
	type SkillDraft = { prompt_block_override: string };
	let toolDrafts = $state<Record<string, ToolDraft>>({});
	let skillDrafts = $state<Record<string, SkillDraft>>({});

	function isHttpConfigurable(tool: ToolActivationResponse): boolean {
		return !tool.endpoint;
	}

	async function refreshRegistryMetadata() {
		const [meta, creds] = await Promise.all([
			registryApi.getMetadata(data.instance.id),
			registryApi.getCredentials()
		]);
		registryMetadata = meta;
		credentials = creds;
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
		return skill.credential_schema?.label as string ?? 'API Key';
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
			variables[spec.name] = cur != null ? String(cur) : spec.default != null ? String(spec.default) : '';
		}
		const http = (cfg.http as Record<string, unknown>) ?? {};
		const httpHeaders = (http.headers as Record<string, string>) ?? {};
		const authorization = httpHeaders['Authorization'] ?? httpHeaders['authorization'] ?? '';
		const headersExtra: Record<string, string> = {};
		for (const [k, v] of Object.entries(httpHeaders)) {
			if (k.toLowerCase() !== 'authorization') headersExtra[k] = v;
		}
		toolDrafts[tool.slug] = {
			prompt_block_override: typeof cfg.prompt_block_override === 'string' ? cfg.prompt_block_override : '',
			variables,
			http: {
				method: typeof http.method === 'string' ? http.method : tool.method ?? 'GET',
				endpoint: typeof http.endpoint === 'string' ? http.endpoint : tool.endpoint ?? '',
				authorization: typeof authorization === 'string' ? authorization : '',
				headers_extra: Object.keys(headersExtra).length > 0 ? JSON.stringify(headersExtra, null, 2) : '',
				body: typeof http.body === 'string' ? http.body : tool.body_template ?? ''
			}
		};
		toolDrafts = { ...toolDrafts };
	}

	function initSkillDraft(skill: SkillActivationResponse) {
		if (skillDrafts[skill.slug]) return;
		const cfg = (skill.config ?? {}) as Record<string, unknown>;
		skillDrafts[skill.slug] = {
			prompt_block_override: typeof cfg.prompt_block_override === 'string' ? cfg.prompt_block_override : ''
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

	async function configureSkill(
		skill: SkillActivationResponse,
		config = skill.config ?? {}
	) {
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

	async function configureTool(
		tool: ToolActivationResponse,
		config = tool.config ?? {}
	) {
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

	async function removeSkill(slug: string) {
		if (!confirm(`Remove skill "${slug}" from this instance?`)) return;
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

	async function removeTool(slug: string) {
		if (!confirm(`Remove tool "${slug}" from this instance?`)) return;
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
		if (!value.trim()) return;
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

	async function deleteCredential(slug: string) {
		if (!confirm(`Remove credential for "${slug}"?`)) return;
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

	function toggleCredentialVisibility(slug: string) {
		credentialVisible[slug] = !credentialVisible[slug];
		credentialVisible = { ...credentialVisible };
	}

	async function saveToolDraft(tool: ToolActivationResponse) {
		const draft = toolDrafts[tool.slug];
		if (!draft) return;
		const baseConfig = (tool.config ?? {}) as Record<string, unknown>;
		const variables: Record<string, string> = {};
		for (const [k, v] of Object.entries(draft.variables)) {
			if (v !== '') variables[k] = v;
		}
		const config: Record<string, unknown> = { ...baseConfig };
		if (Object.keys(variables).length > 0) config.variables = variables;
		else delete config.variables;
		const override = draft.prompt_block_override.trim();
		if (override) config.prompt_block_override = override;
		else delete config.prompt_block_override;

		if (isHttpConfigurable(tool)) {
			if (!draft.http.endpoint.trim()) {
				toast.error('Endpoint is required for web_fetch.');
				return;
			}
			let extraHeaders: Record<string, string> = {};
			if (draft.http.headers_extra.trim()) {
				try {
					const parsed = JSON.parse(draft.http.headers_extra);
					if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
						for (const [k, v] of Object.entries(parsed)) extraHeaders[k] = String(v);
					} else {
						toast.error('Extra headers must be a JSON object.');
						return;
					}
				} catch {
					toast.error('Extra headers JSON is invalid.');
					return;
				}
			}
			const headers: Record<string, string> = { ...extraHeaders };
			if (draft.http.authorization.trim()) headers['Authorization'] = draft.http.authorization.trim();
			const http: Record<string, unknown> = {
				method: draft.http.method,
				endpoint: draft.http.endpoint.trim(),
				headers
			};
			if (draft.http.body.trim()) http.body = draft.http.body;
			config.http = http;
		}

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
		if (!draft) return;
		const baseConfig = (skill.config ?? {}) as Record<string, unknown>;
		const config: Record<string, unknown> = { ...baseConfig };
		const override = draft.prompt_block_override.trim();
		if (override) config.prompt_block_override = override;
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
			if (saved === 0) toast.info('No tool changes to save.');
		} finally {
			setSaving(false);
		}
	}

	onMount(() => {
		register(saveAllDrafts, 'Save changes');
		return () => unregister();
	});
</script>

<div class="mx-auto max-w-3xl space-y-6 px-6 py-5">

	<!-- Skills -->
	<section class="rounded-xl p-6" style="background:var(--surface);border:1px solid var(--ds-border)">
		<div class="mb-4 flex items-center justify-between">
			<div>
				<h3 class="font-display text-sm font-semibold" style="color:var(--text-main)">Skills</h3>
				<p class="mt-0.5 text-xs text-muted-foreground">Instance-level skill activation and configuration</p>
			</div>
			<Button variant="outline" size="sm" onclick={() => (addSkillOpen = true)}>
				<Plus data-icon="inline-start" />
				Add Skill
			</Button>
		</div>

		{#if registryMetadata.skills.length === 0}
			<p class="py-6 text-center text-sm text-muted-foreground">No skills yet. Click "Add Skill" to pick from the catalog.</p>
		{:else}
			<div class="space-y-3">
				{#each registryMetadata.skills as skill (skill.slug)}
					{@const key = `skill:${skill.slug}`}
					{@const busy = registryBusy === key}
					{@const expanded = expandedConfig === key}
					{@const cred = getCredential(skill.slug)}
					<div class="rounded-lg p-4" style="background:var(--surface-hover);border:1px solid var(--ds-border)">
						<div class="flex flex-wrap items-start justify-between gap-3">
							<div class="min-w-0 flex-1">
								<div class="flex items-center gap-2">
									<div class="flex size-8 items-center justify-center rounded-md bg-blue-500/10 text-blue-400">
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
									<Badge variant="outline" class="text-[10px]">{skill.category ?? 'uncategorized'}</Badge>
									<Badge variant="outline" class="text-[10px] font-mono">{skill.executor}</Badge>
									{#if skill.requires_credential}
										<Badge variant="outline" class="text-[10px] text-amber-400 border-amber-400/30">requires credential</Badge>
									{/if}
								</div>
							</div>
							<div class="flex shrink-0 items-center gap-2">
								<Button variant="ghost" size="sm" onclick={() => { initSkillDraft(skill); openConfig(key, skill.slug); }}>
									Config
								</Button>
								<Button
									variant="destructive"
									size="sm"
									disabled={busy}
									onclick={() => removeSkill(skill.slug)}
									title="Remove skill"
								>
									{#if busy}<Spinner data-icon="inline-start" />{/if}
									<Trash2 class="size-3.5" />
								</Button>
							</div>
						</div>
						{#if expanded}
							<div class="mt-4 space-y-4 rounded-lg border bg-[var(--canvas)] p-4 text-sm text-muted-foreground" style="border-color:var(--ds-border)">
								{#if hasSkillConfig(skill)}
									<div>
										<p class="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Configuration</p>
										{#each Object.entries(skill.config!).filter(([k]) => k !== 'prompt_block_override') as [key, value]}
											<div class="mb-2 grid grid-cols-[140px_1fr] gap-2 text-xs">
												<span class="font-mono text-foreground/70">{key}</span>
												<span class="text-foreground/80">{typeof value === 'string' ? value : JSON.stringify(value)}</span>
											</div>
										{/each}
									</div>
								{/if}
								<div>
									<p class="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Instruction (when to use)</p>
									<p class="mb-2 text-[11px] text-muted-foreground/70">Default from registry: <span class="font-mono">{skill.prompt_block}</span></p>
									<textarea
										rows="3"
										placeholder="Leave empty to use the default instruction."
										value={skillDrafts[skill.slug]?.prompt_block_override ?? ''}
										oninput={(e) => {
											if (!skillDrafts[skill.slug]) skillDrafts[skill.slug] = { prompt_block_override: '' };
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
											{#if registryBusy === `skill:${skill.slug}`}<Spinner data-icon="inline-start" />{/if}
											Save instruction
										</Button>
									</div>
								</div>
								{#if skill.requires_credential}
									<div>
										<p class="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{credentialLabel(skill)}</p>
										<div class="flex items-center gap-2">
											<div class="relative flex-1">
												<input
													type={credentialVisible[skill.slug] ? 'text' : 'password'}
													placeholder={cred ? '********' : 'Insert the credential value'}
													value={credentialInputs[skill.slug] ?? ''}
													oninput={(e) => { credentialInputs[skill.slug] = e.currentTarget.value; credentialInputs = { ...credentialInputs }; }}
													class="auth-input w-full rounded-lg px-3.5 py-2.5 pr-10 font-mono text-sm"
												/>
												<button
													onclick={() => toggleCredentialVisibility(skill.slug)}
													class="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
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
												disabled={registryBusy === `cred:${skill.slug}` || !(credentialInputs[skill.slug] ?? '').trim()}
												onclick={() => saveCredential(skill.slug)}
											>
												{#if registryBusy === `cred:${skill.slug}`}<Spinner data-icon="inline-start" />{/if}
												Save
											</Button>
											{#if cred}
												<Button
													variant="destructive"
													size="sm"
													disabled={registryBusy === `cred:${skill.slug}`}
													onclick={() => deleteCredential(skill.slug)}
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
	<section class="rounded-xl p-6" style="background:var(--surface);border:1px solid var(--ds-border)">
		<div class="mb-4 flex items-center justify-between">
			<div>
				<h3 class="font-display text-sm font-semibold" style="color:var(--text-main)">Tools</h3>
				<p class="mt-0.5 text-xs text-muted-foreground">Utility tools available to this agent instance</p>
			</div>
			<Button variant="outline" size="sm" onclick={() => (addToolOpen = true)}>
				<Plus data-icon="inline-start" />
				Add Tool
			</Button>
		</div>

		{#if registryMetadata.tools.length === 0}
			<p class="py-6 text-center text-sm text-muted-foreground">No tools yet. Click "Add Tool" to pick from the catalog.</p>
		{:else}
			<div class="space-y-3">
				{#each registryMetadata.tools as tool (tool.slug)}
					{@const key = `tool:${tool.slug}`}
					{@const busy = registryBusy === key}
					{@const expanded = expandedConfig === key}
					<div class="rounded-lg p-4" style="background:var(--surface-hover);border:1px solid var(--ds-border)">
						<div class="flex flex-wrap items-start justify-between gap-3">
							<div class="min-w-0 flex-1">
								<div class="flex items-center gap-2">
									<div class="flex size-8 items-center justify-center rounded-md bg-blue-500/10 text-blue-400">
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
									<Badge variant="outline" class="text-[10px]">{tool.category ?? 'uncategorized'}</Badge>
									<Badge variant="outline" class="text-[10px] font-mono">{tool.executor}</Badge>
									{#if tool.is_builtin}
										<Badge variant="outline" class="text-[10px] text-emerald-400 border-emerald-400/30">builtin</Badge>
									{/if}
								</div>
							</div>
							<div class="flex shrink-0 items-center gap-2">
								<Button variant="ghost" size="sm" onclick={() => { initToolDraft(tool); openConfig(key); }}>
									Config
								</Button>
								<Button
									variant="destructive"
									size="sm"
									disabled={busy}
									onclick={() => removeTool(tool.slug)}
									title="Remove tool"
								>
									{#if busy}<Spinner data-icon="inline-start" />{/if}
									<Trash2 class="size-3.5" />
								</Button>
							</div>
						</div>
						{#if expanded}
							<div class="mt-4 space-y-4 rounded-lg border bg-[var(--canvas)] p-4 text-sm text-muted-foreground" style="border-color:var(--ds-border)">
								{#if isHttpConfigurable(tool)}
									<div>
										<p class="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">HTTP Request</p>
										<p class="mb-3 text-[11px] text-muted-foreground/70">
											Configure the HTTP request shape for this tool. Use <span class="font-mono">{'{var}'}</span> placeholders to interpolate AI tool-call arguments (defined in the JSON schema).
										</p>
										<div class="space-y-3">
											<div class="grid grid-cols-[120px_1fr] gap-3 items-center">
												<label class="text-xs font-medium text-foreground/80">Method</label>
												<select
													value={toolDrafts[tool.slug]?.http.method ?? 'GET'}
													onchange={(e) => {
														if (!toolDrafts[tool.slug]) initToolDraft(tool);
														toolDrafts[tool.slug].http.method = e.currentTarget.value;
														toolDrafts = { ...toolDrafts };
													}}
													class="auth-input rounded-lg px-3 py-2 text-sm"
												>
													<option value="GET">GET</option>
													<option value="POST">POST</option>
													<option value="PUT">PUT</option>
													<option value="PATCH">PATCH</option>
													<option value="DELETE">DELETE</option>
												</select>
											</div>
											<div>
												<label class="mb-1 block text-xs font-medium text-foreground/80">Endpoint <span class="text-red-400">*</span></label>
												<input
													type="text"
													placeholder={'https://api.example.com/v1/users/{id}'}
													value={toolDrafts[tool.slug]?.http.endpoint ?? ''}
													oninput={(e) => {
														if (!toolDrafts[tool.slug]) initToolDraft(tool);
														toolDrafts[tool.slug].http.endpoint = e.currentTarget.value;
														toolDrafts = { ...toolDrafts };
													}}
													class="auth-input w-full rounded-lg px-3.5 py-2.5 font-mono text-sm"
												/>
											</div>
											<div>
												<label class="mb-1 block text-xs font-medium text-foreground/80">Authorization header</label>
												<p class="mb-1 text-[11px] text-muted-foreground/70">e.g. <span class="font-mono">Bearer ey...</span>, <span class="font-mono">Basic ...</span></p>
												<input
													type="text"
													placeholder="Leave empty if no auth required."
													value={toolDrafts[tool.slug]?.http.authorization ?? ''}
													oninput={(e) => {
														if (!toolDrafts[tool.slug]) initToolDraft(tool);
														toolDrafts[tool.slug].http.authorization = e.currentTarget.value;
														toolDrafts = { ...toolDrafts };
													}}
													class="auth-input w-full rounded-lg px-3.5 py-2.5 font-mono text-sm"
												/>
											</div>
											<div>
												<label class="mb-1 block text-xs font-medium text-foreground/80">Extra headers (JSON)</label>
												<textarea
													rows="3"
													placeholder={'{ "Content-Type": "application/json" }'}
													value={toolDrafts[tool.slug]?.http.headers_extra ?? ''}
													oninput={(e) => {
														if (!toolDrafts[tool.slug]) initToolDraft(tool);
														toolDrafts[tool.slug].http.headers_extra = e.currentTarget.value;
														toolDrafts = { ...toolDrafts };
													}}
													class="auth-input w-full rounded-lg px-3.5 py-2.5 font-mono text-xs"
												></textarea>
											</div>
											<div>
												<label class="mb-1 block text-xs font-medium text-foreground/80">Body / payload template</label>
												<p class="mb-1 text-[11px] text-muted-foreground/70">Used for POST/PUT/PATCH. Placeholders allowed.</p>
												<textarea
													rows="4"
													placeholder={'{ "query": "{query}" }'}
													value={toolDrafts[tool.slug]?.http.body ?? ''}
													oninput={(e) => {
														if (!toolDrafts[tool.slug]) initToolDraft(tool);
														toolDrafts[tool.slug].http.body = e.currentTarget.value;
														toolDrafts = { ...toolDrafts };
													}}
													class="auth-input w-full rounded-lg px-3.5 py-2.5 font-mono text-xs"
												></textarea>
											</div>
										</div>
									</div>
								{:else if tool.endpoint}
									<div>
										<p class="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">HTTP Request</p>
										<div class="grid grid-cols-[80px_1fr] gap-2 text-xs">
											<span class="font-mono text-foreground/70">method</span>
											<span class="font-mono text-foreground/80">{tool.method ?? 'GET'}</span>
											<span class="font-mono text-foreground/70">endpoint</span>
											<span class="font-mono break-all text-foreground/80">{tool.endpoint}</span>
											{#if tool.headers_template && Object.keys(tool.headers_template).length > 0}
												<span class="font-mono text-foreground/70">headers</span>
												<span class="font-mono break-all text-foreground/80">{JSON.stringify(tool.headers_template)}</span>
											{/if}
											{#if tool.body_template}
												<span class="font-mono text-foreground/70">body</span>
												<span class="font-mono break-all text-foreground/80">{tool.body_template}</span>
											{/if}
										</div>
									</div>
								{/if}
								{#if toolVariableSpecs(tool).length > 0}
									<div>
										<p class="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Variables</p>
										<div class="space-y-2">
											{#each toolVariableSpecs(tool) as spec (spec.name)}
												<div>
													<label class="mb-1 block text-xs font-medium text-foreground/80">
														{spec.label ?? spec.name}
														{#if spec.required}<span class="text-red-400">*</span>{/if}
													</label>
													{#if spec.description}
														<p class="mb-1 text-[11px] text-muted-foreground/70">{spec.description}</p>
													{/if}
													<input
														type={spec.secret ? 'password' : 'text'}
														placeholder={spec.default != null ? String(spec.default) : ''}
														value={toolDrafts[tool.slug]?.variables[spec.name] ?? ''}
														oninput={(e) => {
															if (!toolDrafts[tool.slug]) initToolDraft(tool);
															toolDrafts[tool.slug].variables[spec.name] = e.currentTarget.value;
															toolDrafts = { ...toolDrafts };
														}}
														class="auth-input w-full rounded-lg px-3.5 py-2.5 font-mono text-sm"
													/>
												</div>
											{/each}
										</div>
									</div>
								{/if}
								<div>
									<p class="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Instruction (when to use)</p>
									<p class="mb-2 text-[11px] text-muted-foreground/70">Default from registry: <span class="font-mono">{tool.prompt_block}</span></p>
									<textarea
										rows="3"
										placeholder="Leave empty to use the default instruction."
										value={toolDrafts[tool.slug]?.prompt_block_override ?? ''}
										oninput={(e) => {
											if (!toolDrafts[tool.slug]) initToolDraft(tool);
											toolDrafts[tool.slug].prompt_block_override = e.currentTarget.value;
											toolDrafts = { ...toolDrafts };
										}}
										class="auth-input w-full rounded-lg px-3.5 py-2.5 text-sm"
									></textarea>
								</div>
								<div class="flex justify-end">
									<Button
										variant="default"
										size="sm"
										disabled={registryBusy === `tool:${tool.slug}`}
										onclick={() => saveToolDraft(tool)}
									>
										{#if registryBusy === `tool:${tool.slug}`}<Spinner data-icon="inline-start" />{/if}
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
