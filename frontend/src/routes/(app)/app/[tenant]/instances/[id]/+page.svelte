<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Save from '@lucide/svelte/icons/save';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Plus from '@lucide/svelte/icons/plus';
	import GripVertical from '@lucide/svelte/icons/grip-vertical';
	import X from '@lucide/svelte/icons/x';
	import Database from '@lucide/svelte/icons/database';
	import Bot from '@lucide/svelte/icons/bot';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import MoreHorizontal from '@lucide/svelte/icons/more-horizontal';
	import Send from '@lucide/svelte/icons/send';
	import SettingsIcon from '@lucide/svelte/icons/settings';
	import ThumbsDown from '@lucide/svelte/icons/thumbs-down';
	import ThumbsUp from '@lucide/svelte/icons/thumbs-up';
	import JsonConfigPanel from '$lib/components/JsonConfigPanel.svelte';
	import { instancesApi } from '$lib/api/instances';
	import { registryApi } from '$lib/api/registry';
	import { ApiError, getErrorMessage } from '$lib/api/client';
	import { tenantBaseFromPath } from '$lib/routes/tenant';
	import { getAgentUiSettings } from '$lib/settings/agent-ui';
	import { toast } from 'svelte-sonner';
	import type {
		AgentInstanceResponse,
		AgentPromptConfigResponse,
		AgentInstructionBlock,
		AgentGuardrail,
		SkillActivationResponse,
		ToolActivationResponse,
		ToolMetadataResponse
	} from '$lib/api/types';

	let { data } = $props();
	const id = $derived(data.instance.id);
	const appBase = $derived(tenantBaseFromPath(page.url.pathname));
	const agentUi = getAgentUiSettings(data.publicSettings);

	// ── State ────────────────────────────────────────────────────────────────
	let instance = $state<AgentInstanceResponse>(data.instance);
	let promptConfig = $state<AgentPromptConfigResponse>(data.promptConfig);
	let registryMetadata = $state<ToolMetadataResponse>(data.registryMetadata);
	let error = $state('');
	let activeTab = $state<'config' | 'prompt' | 'skills'>('config');

	// Config form state
	let name = $state(data.instance.name);
	let description = $state(data.instance.description ?? '');
	let core_prompt = $state(data.instance.core_prompt);
	let model = $state(data.instance.model);
	let temperature = $state(data.instance.temperature);
	let rag_scope = $state(data.instance.rag_scope ?? 'none');
	let saving = $state(false);
	let saveError = $state('');
	let saveOk = $state(false);

	// Prompt config state
	let blocks = $state<AgentInstructionBlock[]>([...(data.promptConfig.instruction_blocks ?? [])]);
	let guardrails = $state<AgentGuardrail[]>([...(data.promptConfig.guardrails ?? [])]);
	let promptSaving = $state(false);
	let promptError = $state('');
	let promptOk = $state(false);

	// Registry state
	let registryBusy = $state('');
	let expandedConfig = $state('');

	// New block form
	let newBlock = $state({ topic: '', title: '', content: '', priority: 10, is_enabled: true });
	let addingBlock = $state(false);

	// New guardrail form
	let newGuardrail = $state({ category: 'safety', rule: '', severity: 'medium', is_enabled: true });
	let addingGuardrail = $state(false);
	let testMessage = $state('');

	const MODELS = agentUi.models.map((item) => item.value);
	const RAG_SCOPES = ['none', 'tenant', 'instance'];
	const SEVERITY = ['low', 'medium', 'high', 'critical'];

	// ── Load ─────────────────────────────────────────────────────────────────
	// ── Config save ───────────────────────────────────────────────────────────
	async function saveConfig() {
		if (!name.trim()) {
			saveError = 'Name is required.';
			return;
		}
		if (!core_prompt.trim()) {
			saveError = 'Core prompt is required.';
			return;
		}
		if (temperature < 0 || temperature > 2) {
			saveError = 'Temperature must be between 0 and 2.';
			return;
		}
		saveError = '';
		saveOk = false;
		saving = true;
		try {
			instance = await instancesApi.update(id, {
				name: name.trim(),
				description: description.trim() || undefined,
				core_prompt: core_prompt.trim(),
				model,
				temperature,
				rag_scope: rag_scope === 'none' ? undefined : rag_scope
			});
			saveOk = true;
			setTimeout(() => {
				saveOk = false;
			}, 2500);
		} catch (err) {
			saveError = err instanceof ApiError ? err.message : 'Save failed.';
		} finally {
			saving = false;
		}
	}

	// ── Delete instance ───────────────────────────────────────────────────────
	async function deleteInstance() {
		if (!confirm(`Delete "${instance?.name}"? This cannot be undone.`)) return;
		try {
			await instancesApi.delete(id);
			await goto(`${appBase}/instances`);
		} catch (err) {
			saveError = err instanceof ApiError ? err.message : 'Delete failed.';
		}
	}

	// ── Prompt config save ────────────────────────────────────────────────────
	async function savePromptConfig() {
		promptError = '';
		promptOk = false;
		promptSaving = true;
		try {
			const normalizedBlocks = blocks
				.filter((block) => block.topic.trim() && block.content.trim())
				.map((block, index) => ({
					...block,
					topic: block.topic.trim(),
					title: block.title?.trim() ?? '',
					content: block.content.trim(),
					priority: index + 1
				}));
			const normalizedGuardrails = guardrails
				.filter((guardrail) => guardrail.category.trim() && guardrail.rule.trim())
				.map((guardrail) => ({
					...guardrail,
					category: guardrail.category.trim(),
					rule: guardrail.rule.trim()
				}));
			const cfg = await instancesApi.savePromptConfig(id, {
				instruction_blocks: normalizedBlocks,
				guardrails: normalizedGuardrails
			});
			promptConfig = cfg;
			blocks = [...(cfg.instruction_blocks ?? [])];
			guardrails = [...(cfg.guardrails ?? [])];
			promptOk = true;
			setTimeout(() => {
				promptOk = false;
			}, 2500);
		} catch (err) {
			promptError = err instanceof ApiError ? err.message : 'Save failed.';
		} finally {
			promptSaving = false;
		}
	}

	// ── Instruction blocks ────────────────────────────────────────────────────
	function addBlock() {
		if (!newBlock.topic.trim() || !newBlock.content.trim()) return;
		blocks = [
			...blocks,
			{
				...newBlock,
				topic: newBlock.topic.trim(),
				title: newBlock.title.trim(),
				content: newBlock.content.trim()
			}
		];
		newBlock = { topic: '', title: '', content: '', priority: 10, is_enabled: true };
		addingBlock = false;
	}

	function removeBlock(i: number) {
		blocks = blocks.filter((_, idx) => idx !== i);
	}

	function moveBlock(i: number, dir: -1 | 1) {
		const j = i + dir;
		if (j < 0 || j >= blocks.length) return;
		const arr = [...blocks];
		[arr[i], arr[j]] = [arr[j], arr[i]];
		blocks = arr;
	}

	function toggleBlock(i: number) {
		blocks = blocks.map((b, idx) => (idx === i ? { ...b, is_enabled: !b.is_enabled } : b));
	}

	function updateBlock(i: number, patch: Partial<AgentInstructionBlock>) {
		blocks = blocks.map((block, idx) => (idx === i ? { ...block, ...patch } : block));
	}

	// ── Guardrails ────────────────────────────────────────────────────────────
	function addGuardrail() {
		if (!newGuardrail.rule.trim()) return;
		guardrails = [...guardrails, { ...newGuardrail, rule: newGuardrail.rule.trim() }];
		newGuardrail = { category: 'safety', rule: '', severity: 'medium', is_enabled: true };
		addingGuardrail = false;
	}

	function removeGuardrail(i: number) {
		guardrails = guardrails.filter((_, idx) => idx !== i);
	}

	function toggleGuardrail(i: number) {
		guardrails = guardrails.map((g, idx) => (idx === i ? { ...g, is_enabled: !g.is_enabled } : g));
	}

	function updateGuardrail(i: number, patch: Partial<AgentGuardrail>) {
		guardrails = guardrails.map((guardrail, idx) =>
			idx === i ? { ...guardrail, ...patch } : guardrail
		);
	}

	async function refreshRegistryMetadata() {
		registryMetadata = await registryApi.getMetadata(id);
	}

	async function configureSkill(
		skill: SkillActivationResponse,
		is_enabled = skill.is_enabled,
		config = skill.config ?? {}
	) {
		registryBusy = `skill:${skill.skill_slug}`;
		try {
			await registryApi.activateSkill(id, skill.skill_slug, { is_enabled, config });
			await refreshRegistryMetadata();
			toast.success('Skill configuration updated.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Skill update failed.'));
		} finally {
			registryBusy = '';
		}
	}

	async function configureTool(
		tool: ToolActivationResponse,
		is_enabled = tool.is_enabled,
		config = tool.config ?? {}
	) {
		registryBusy = `tool:${tool.tool_slug}`;
		try {
			await registryApi.activateToolItem(id, tool.tool_slug, { is_enabled, config });
			await refreshRegistryMetadata();
			toast.success('Tool configuration updated.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Tool update failed.'));
		} finally {
			registryBusy = '';
		}
	}

	function parseJsonConfig(json: string): Record<string, unknown> {
		return JSON.parse(json || '{}') as Record<string, unknown>;
	}
</script>

{#if error}
	<div
		class="rounded-xl px-4 py-3 text-sm text-red-400"
		style="background:color-mix(in srgb,red 8%,transparent);border:1px solid color-mix(in srgb,red 18%,transparent)"
	>
		{error}
	</div>
{/if}

{#if !error}
	<header
		class="sticky top-0 z-10 flex h-14 items-center justify-between gap-4 border-b bg-[var(--surface)] px-5 lg:mr-[420px]"
		style="border-color:var(--ds-border)"
	>
		<div class="flex min-w-0 items-center gap-3">
			<a
				href="{appBase}/instances"
				class="rounded-md p-1.5 transition-colors hover:bg-[var(--surface-hover)]"
				aria-label="Back to agents"
			>
				<ArrowLeft class="h-4 w-4 text-muted-foreground" />
			</a>
			<div
				class="flex size-8 shrink-0 items-center justify-center rounded-full border bg-blue-500/10 text-blue-500"
				style="border-color:color-mix(in srgb, var(--ds-border) 70%, #3b82f6 30%)"
			>
				<Bot class="size-4" />
			</div>
			<div class="min-w-0">
				<div class="flex items-center gap-2">
					<h1 class="truncate text-sm font-semibold" style="color:var(--text-main)">
						{instance.name}
					</h1>
				</div>
			</div>

			<div class="flex shrink-0 items-center gap-2">
				<button
					class="rounded-md border px-3 py-1.5 text-xs font-semibold transition-colors hover:bg-[var(--surface-hover)]"
					style="border-color:var(--ds-border)">Publish</button
				>
				<button
					class="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-semibold transition-colors hover:bg-[var(--surface-hover)]"
					style="border-color:var(--ds-border)"
				>
					<SettingsIcon class="size-3.5" />
					Settings
				</button>
				<button
					class="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-[var(--surface-hover)] hover:text-foreground"
					aria-label="More actions"
				>
					<MoreHorizontal class="size-4" />
				</button>
				<button
					onclick={deleteInstance}
					class="rounded-md p-1.5 text-red-400 transition-colors hover:bg-red-400/10"
					aria-label="Delete agent"
				>
					<Trash2 class="h-4 w-4" />
				</button>
			</div>
		</div>
	</header>

	<nav
		class="flex h-11 items-center gap-5 border-b bg-[var(--surface)] px-6 text-xs lg:mr-[420px]"
		style="border-color:var(--ds-border)"
	>
		{#each [['config', 'Overview'], ['prompt', 'Instructions'], ['skills', 'Tools']] as [tab, label] (tab)}
			<button
				onclick={() => {
					activeTab = tab as typeof activeTab;
				}}
				class="relative h-full font-semibold transition-colors {activeTab === tab
					? 'text-blue-500'
					: 'text-muted-foreground hover:text-foreground'}"
			>
				{label}
				{#if activeTab === tab}
					<span class="absolute inset-x-0 bottom-0 h-0.5 rounded-full bg-blue-500"></span>
				{/if}
			</button>
		{/each}
		<a
			href="{appBase}/collections"
			class="font-semibold text-muted-foreground transition-colors hover:text-foreground"
			>Knowledge</a
		>
	</nav>

	<!-- ── Tab: Config ──────────────────────────────────────────────────────── -->
	{#if activeTab === 'config'}
		<div class="mx-auto max-w-5xl space-y-5 px-6 py-5 lg:mr-[420px]">
			{#if saveError}
				<div
					class="rounded-xl px-4 py-3 text-sm text-red-400"
					style="background:color-mix(in srgb,red 8%,transparent);border:1px solid color-mix(in srgb,red 18%,transparent)"
				>
					{saveError}
				</div>
			{/if}
			{#if saveOk}
				<div
					class="rounded-xl px-4 py-3 text-sm text-emerald-400"
					style="background:color-mix(in srgb,emerald 8%,transparent);border:1px solid color-mix(in srgb,emerald 18%,transparent)"
				>
					Saved successfully.
				</div>
			{/if}

			<div
				class="space-y-5 rounded-xl p-6"
				style="background:var(--surface);border:1px solid var(--ds-border)"
			>
				<div class="flex items-center justify-between">
					<div>
						<h2 class="font-display text-sm font-semibold" style="color:var(--text-main)">
							Details
						</h2>
						<p class="mt-1 text-xs text-muted-foreground">
							Agent identity, description and runtime model.
						</p>
					</div>
					<span
						class="rounded-full bg-white/5 px-2 py-1 text-[10px] font-semibold text-muted-foreground uppercase"
						>{instance.status}</span
					>
				</div>
				<div class="space-y-1.5">
					<label
						class="block text-[11px] font-semibold tracking-widest text-muted-foreground uppercase"
						>Name *</label
					>
					<input
						type="text"
						bind:value={name}
						class="auth-input w-full rounded-lg px-3.5 py-2.5 text-sm"
					/>
				</div>
				<div class="space-y-1.5">
					<label
						class="block text-[11px] font-semibold tracking-widest text-muted-foreground uppercase"
						>Description</label
					>
					<input
						type="text"
						bind:value={description}
						class="auth-input w-full rounded-lg px-3.5 py-2.5 text-sm"
					/>
				</div>
				<div class="grid grid-cols-2 gap-4">
					<div class="space-y-1.5">
						<label
							class="block text-[11px] font-semibold tracking-widest text-muted-foreground uppercase"
							>Model</label
						>
						<select bind:value={model} class="auth-input w-full rounded-lg px-3.5 py-2.5 text-sm">
							{#each MODELS as m (m)}<option value={m}>{m}</option>{/each}
						</select>
					</div>
					<div class="space-y-1.5">
						<label
							class="block text-[11px] font-semibold tracking-widest text-muted-foreground uppercase"
						>
							Temperature — <span class="font-mono text-blue-400">{temperature.toFixed(1)}</span>
						</label>
						<input
							type="range"
							bind:value={temperature}
							min="0"
							max="2"
							step="0.1"
							class="mt-3 w-full accent-blue-500"
						/>
					</div>
				</div>
				<div class="space-y-1.5">
					<label
						class="block text-[11px] font-semibold tracking-widest text-muted-foreground uppercase"
						>RAG scope</label
					>
					<select bind:value={rag_scope} class="auth-input w-full rounded-lg px-3.5 py-2.5 text-sm">
						{#each RAG_SCOPES as s (s)}<option value={s}>{s}</option>{/each}
					</select>
				</div>
			</div>

			<div
				class="space-y-3 rounded-xl p-6"
				style="background:var(--surface);border:1px solid var(--ds-border)"
			>
				<div>
					<h2 class="font-display text-sm font-semibold" style="color:var(--text-main)">
						Instructions
					</h2>
					<p class="mt-1 text-xs text-muted-foreground">
						Base behavior for this agent. Topic-specific blocks live in the Instructions tab.
					</p>
				</div>
				<label
					class="block text-[11px] font-semibold tracking-widest text-muted-foreground uppercase"
					>Core prompt *</label
				>
				<textarea
					bind:value={core_prompt}
					rows="10"
					class="auth-input w-full resize-y rounded-lg px-3.5 py-2.5 font-mono text-sm leading-relaxed"
				></textarea>
			</div>

			<div
				class="rounded-xl p-6"
				style="background:var(--surface);border:1px solid var(--ds-border)"
			>
				<div class="flex items-center justify-between gap-4">
					<div class="flex items-center gap-3">
						<div
							class="flex size-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400"
						>
							<Database class="size-5" />
						</div>
						<div>
							<h2 class="font-display text-sm font-semibold" style="color:var(--text-main)">
								Knowledge
							</h2>
							<p class="mt-1 text-sm text-muted-foreground">
								Add data, files and collections to improve agent responses.
							</p>
						</div>
					</div>
					<a
						href="{appBase}/collections"
						class="rounded-lg border px-3 py-2 text-sm font-semibold transition-colors hover:bg-white/5"
						style="border-color:var(--ds-border)"
					>
						Manage Collections
					</a>
				</div>
			</div>

			<div class="flex justify-end">
				<button
					onclick={saveConfig}
					disabled={saving}
					class="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:opacity-60"
				>
					<Save class="h-4 w-4" />
					{saving ? 'Saving...' : 'Save changes'}
				</button>
			</div>
		</div>

		<!-- ── Tab: Prompt Config ────────────────────────────────────────────────── -->
	{:else if activeTab === 'prompt'}
		<div class="mx-auto max-w-2xl space-y-6 px-6 py-5 lg:mr-[420px]">
			{#if promptError}
				<div
					class="rounded-xl px-4 py-3 text-sm text-red-400"
					style="background:color-mix(in srgb,red 8%,transparent);border:1px solid color-mix(in srgb,red 18%,transparent)"
				>
					{promptError}
				</div>
			{/if}
			{#if promptOk}
				<div
					class="rounded-xl px-4 py-3 text-sm text-emerald-400"
					style="background:color-mix(in srgb,emerald 8%,transparent);border:1px solid color-mix(in srgb,emerald 18%,transparent)"
				>
					Prompt config saved.
				</div>
			{/if}

			<!-- Instruction blocks -->
			<div
				class="rounded-xl p-6"
				style="background:var(--surface);border:1px solid var(--ds-border)"
			>
				<div class="mb-4 flex items-center justify-between">
					<div>
						<h3 class="font-display text-sm font-semibold" style="color:var(--text-main)">
							Instruction blocks
						</h3>
						<p class="mt-0.5 text-xs text-muted-foreground">
							Custom instruction sections injected into the prompt
						</p>
					</div>
					<button
						onclick={() => {
							addingBlock = !addingBlock;
						}}
						class="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-blue-400 transition-colors hover:bg-blue-400/10"
					>
						<Plus class="h-3.5 w-3.5" />
						Add block
					</button>
				</div>

				{#if addingBlock}
					<div
						class="mb-4 space-y-3 rounded-lg p-4"
						style="background:var(--surface-hover);border:1px solid var(--ds-border-hover)"
					>
						<div class="grid grid-cols-2 gap-3">
							<div class="space-y-1">
								<label
									class="block text-[10px] font-semibold tracking-widest text-muted-foreground uppercase"
									>Topic *</label
								>
								<input
									type="text"
									bind:value={newBlock.topic}
									placeholder="e.g. tone"
									class="auth-input w-full rounded-lg px-3 py-2 text-sm"
								/>
							</div>
							<div class="space-y-1">
								<label
									class="block text-[10px] font-semibold tracking-widest text-muted-foreground uppercase"
									>Title</label
								>
								<input
									type="text"
									bind:value={newBlock.title}
									placeholder="Display title"
									class="auth-input w-full rounded-lg px-3 py-2 text-sm"
								/>
							</div>
						</div>
						<div class="space-y-1">
							<label
								class="block text-[10px] font-semibold tracking-widest text-muted-foreground uppercase"
								>Content *</label
							>
							<textarea
								bind:value={newBlock.content}
								rows="3"
								placeholder="Instruction text..."
								class="auth-input w-full resize-none rounded-lg px-3 py-2 font-mono text-sm"
							></textarea>
						</div>
						<div class="flex items-center justify-between">
							<div class="flex items-center gap-2">
								<label
									class="text-[10px] font-semibold tracking-widest text-muted-foreground uppercase"
									>Priority</label
								>
								<input
									type="number"
									bind:value={newBlock.priority}
									min="1"
									max="100"
									class="auth-input w-16 rounded-lg px-2 py-1 text-center font-mono text-sm"
								/>
							</div>
							<div class="flex gap-2">
								<button
									onclick={() => {
										addingBlock = false;
									}}
									class="rounded-lg px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground"
									>Cancel</button
								>
								<button
									onclick={addBlock}
									class="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-500"
									>Add</button
								>
							</div>
						</div>
					</div>
				{/if}

				{#if blocks.length === 0}
					<p class="py-4 text-center text-sm text-muted-foreground">No instruction blocks yet.</p>
				{:else}
					<div class="space-y-2">
						{#each blocks as blk, i (i)}
							<div
								class="rounded-lg px-4 py-3"
								style="background:var(--surface-hover);border:1px solid var(--ds-border);opacity:{blk.is_enabled
									? 1
									: 0.5}"
							>
								<div class="flex items-start gap-3">
									<GripVertical class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground/30" />
									<div class="min-w-0 flex-1">
										<div class="flex items-center gap-2">
											<input
												value={blk.topic}
												oninput={(event) => updateBlock(i, { topic: event.currentTarget.value })}
												class="auth-input min-w-0 flex-1 rounded px-2 py-1 text-sm font-semibold"
												placeholder="Topic"
											/>
											{#if blk.title}<span class="text-xs text-muted-foreground">— {blk.title}</span
												>{/if}
											<span class="ml-auto font-mono text-[10px] text-muted-foreground/50"
												>p{blk.priority}</span
											>
										</div>
										<textarea
											value={blk.content}
											oninput={(event) => updateBlock(i, { content: event.currentTarget.value })}
											rows="2"
											class="auth-input mt-2 w-full resize-y rounded px-2 py-1 font-mono text-xs"
											placeholder="Instruction content"
										></textarea>
									</div>
									<div class="flex shrink-0 items-center gap-1">
										<button
											onclick={() => moveBlock(i, -1)}
											disabled={i === 0}
											class="rounded p-1 text-muted-foreground/50 hover:text-foreground disabled:opacity-30"
											>↑</button
										>
										<button
											onclick={() => moveBlock(i, 1)}
											disabled={i === blocks.length - 1}
											class="rounded p-1 text-muted-foreground/50 hover:text-foreground disabled:opacity-30"
											>↓</button
										>
										<button
											onclick={() => toggleBlock(i)}
											class="rounded p-1 text-muted-foreground/50 hover:text-blue-400"
											>{blk.is_enabled ? '●' : '○'}</button
										>
										<button
											onclick={() => removeBlock(i)}
											class="rounded p-1 text-muted-foreground/50 hover:text-red-400"
											><X class="h-3.5 w-3.5" /></button
										>
									</div>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Guardrails -->
			<div
				class="rounded-xl p-6"
				style="background:var(--surface);border:1px solid var(--ds-border)"
			>
				<div class="mb-4 flex items-center justify-between">
					<div>
						<h3 class="font-display text-sm font-semibold" style="color:var(--text-main)">
							Guardrails
						</h3>
						<p class="mt-0.5 text-xs text-muted-foreground">Rules to constrain agent behaviour</p>
					</div>
					<button
						onclick={() => {
							addingGuardrail = !addingGuardrail;
						}}
						class="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-blue-400 transition-colors hover:bg-blue-400/10"
					>
						<Plus class="h-3.5 w-3.5" />
						Add rule
					</button>
				</div>

				{#if addingGuardrail}
					<div
						class="mb-4 space-y-3 rounded-lg p-4"
						style="background:var(--surface-hover);border:1px solid var(--ds-border-hover)"
					>
						<div class="grid grid-cols-2 gap-3">
							<div class="space-y-1">
								<label
									class="block text-[10px] font-semibold tracking-widest text-muted-foreground uppercase"
									>Category</label
								>
								<input
									type="text"
									bind:value={newGuardrail.category}
									class="auth-input w-full rounded-lg px-3 py-2 text-sm"
								/>
							</div>
							<div class="space-y-1">
								<label
									class="block text-[10px] font-semibold tracking-widest text-muted-foreground uppercase"
									>Severity</label
								>
								<select
									bind:value={newGuardrail.severity}
									class="auth-input w-full rounded-lg px-3 py-2 text-sm"
								>
									{#each SEVERITY as s (s)}<option value={s}>{s}</option>{/each}
								</select>
							</div>
						</div>
						<div class="space-y-1">
							<label
								class="block text-[10px] font-semibold tracking-widest text-muted-foreground uppercase"
								>Rule *</label
							>
							<textarea
								bind:value={newGuardrail.rule}
								rows="2"
								placeholder="Never discuss..."
								class="auth-input w-full resize-none rounded-lg px-3 py-2 text-sm"
							></textarea>
						</div>
						<div class="flex justify-end gap-2">
							<button
								onclick={() => {
									addingGuardrail = false;
								}}
								class="rounded-lg px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground"
								>Cancel</button
							>
							<button
								onclick={addGuardrail}
								class="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-500"
								>Add</button
							>
						</div>
					</div>
				{/if}

				{#if guardrails.length === 0}
					<p class="py-4 text-center text-sm text-muted-foreground">No guardrails configured.</p>
				{:else}
					<div class="space-y-2">
						{#each guardrails as g, i (i)}
							<div
								class="flex items-start gap-3 rounded-lg px-4 py-3"
								style="background:var(--surface-hover);border:1px solid var(--ds-border);opacity:{g.is_enabled
									? 1
									: 0.5}"
							>
								<div class="min-w-0 flex-1">
									<div class="flex items-center gap-2">
										<input
											value={g.category}
											oninput={(event) =>
												updateGuardrail(i, { category: event.currentTarget.value })}
											class="auth-input rounded px-2 py-1 text-xs font-semibold"
											placeholder="Category"
										/>
										<select
											value={g.severity}
											onchange={(event) =>
												updateGuardrail(i, { severity: event.currentTarget.value })}
											class="auth-input rounded px-2 py-1 text-[10px] font-semibold uppercase"
										>
											{#each SEVERITY as s (s)}<option value={s}>{s}</option>{/each}
										</select>
									</div>
									<textarea
										value={g.rule}
										oninput={(event) => updateGuardrail(i, { rule: event.currentTarget.value })}
										rows="2"
										class="auth-input mt-2 w-full resize-y rounded px-2 py-1 text-sm"
										placeholder="Guardrail rule"
									></textarea>
								</div>
								<div class="flex shrink-0 items-center gap-1">
									<button
										onclick={() => toggleGuardrail(i)}
										class="rounded p-1 text-muted-foreground/50 hover:text-blue-400"
										>{g.is_enabled ? '●' : '○'}</button
									>
									<button
										onclick={() => removeGuardrail(i)}
										class="rounded p-1 text-muted-foreground/50 hover:text-red-400"
										><X class="h-3.5 w-3.5" /></button
									>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>

			<div class="flex justify-end">
				<button
					onclick={savePromptConfig}
					disabled={promptSaving}
					class="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:opacity-60"
				>
					<Save class="h-4 w-4" />
					{promptSaving ? 'Saving...' : 'Save prompt config'}
				</button>
			</div>
		</div>

		<!-- ── Tab: Skills/Tools ─────────────────────────────────────────────────── -->
	{:else if activeTab === 'skills'}
		<div class="mx-auto max-w-3xl space-y-6 px-6 py-5 lg:mr-[420px]">
			<section
				class="rounded-xl p-6"
				style="background:var(--surface);border:1px solid var(--ds-border)"
			>
				<div class="mb-4 flex items-center justify-between gap-4">
					<div>
						<h3 class="font-display text-sm font-semibold" style="color:var(--text-main)">
							Skills
						</h3>
						<p class="mt-0.5 text-xs text-muted-foreground">
							Instance-level skill activation and config
						</p>
					</div>
				</div>

				{#if registryMetadata.skills.length === 0}
					<p class="py-4 text-center text-sm text-muted-foreground">
						No skills configured for this instance.
					</p>
				{:else}
					<div class="space-y-3">
						{#each registryMetadata.skills as skill (skill.skill_slug)}
							{@const busy = registryBusy === `skill:${skill.skill_slug}`}
							{@const configKey = `skill:${skill.skill_slug}`}
							<div
								class="rounded-lg p-4"
								style="background:var(--surface-hover);border:1px solid var(--ds-border)"
							>
								<div class="flex flex-wrap items-center justify-between gap-3">
									<div class="min-w-0">
										<p class="font-mono text-sm font-semibold" style="color:var(--text-main)">
											{skill.skill_slug}
										</p>
										<p class="mt-0.5 text-xs text-muted-foreground/70">{skill.skill_id}</p>
									</div>
									<div class="flex items-center gap-2">
										<span
											class="rounded-full px-2 py-1 text-[10px] font-semibold uppercase {skill.is_enabled
												? 'bg-emerald-500/10 text-emerald-400'
												: 'bg-white/5 text-muted-foreground'}"
										>
											{skill.is_enabled ? 'Enabled' : 'Disabled'}
										</span>
										<button
											onclick={() => configureSkill(skill, !skill.is_enabled, skill.config ?? {})}
											disabled={busy}
											class="rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors {skill.is_enabled
												? 'text-red-400 hover:bg-red-400/10'
												: 'text-blue-400 hover:bg-blue-400/10'} disabled:opacity-60"
										>
											{busy ? 'Saving...' : skill.is_enabled ? 'Disable' : 'Enable'}
										</button>
										<button
											onclick={() => {
												expandedConfig = expandedConfig === configKey ? '' : configKey;
											}}
											class="rounded-lg px-3 py-1.5 text-xs font-semibold text-muted-foreground transition-colors hover:bg-white/5 hover:text-foreground"
										>
											Config
										</button>
									</div>
								</div>
								{#if expandedConfig === configKey}
									<div class="mt-4">
										<JsonConfigPanel
											value={JSON.stringify(skill.config ?? {}, null, 2)}
											onSave={(json) =>
												configureSkill(skill, skill.is_enabled, parseJsonConfig(json))}
										/>
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{/if}
			</section>

			<section
				class="rounded-xl p-6"
				style="background:var(--surface);border:1px solid var(--ds-border)"
			>
				<div class="mb-4 flex items-center justify-between gap-4">
					<div>
						<h3 class="font-display text-sm font-semibold" style="color:var(--text-main)">Tools</h3>
						<p class="mt-0.5 text-xs text-muted-foreground">
							Utility tools available to this agent instance
						</p>
					</div>
				</div>

				{#if registryMetadata.tools.length === 0}
					<p class="py-4 text-center text-sm text-muted-foreground">
						No tools configured for this instance.
					</p>
				{:else}
					<div class="space-y-3">
						{#each registryMetadata.tools as tool (tool.tool_slug)}
							{@const busy = registryBusy === `tool:${tool.tool_slug}`}
							{@const configKey = `tool:${tool.tool_slug}`}
							<div
								class="rounded-lg p-4"
								style="background:var(--surface-hover);border:1px solid var(--ds-border)"
							>
								<div class="flex flex-wrap items-center justify-between gap-3">
									<div class="min-w-0">
										<p class="font-mono text-sm font-semibold" style="color:var(--text-main)">
											{tool.tool_slug}
										</p>
										<p class="mt-0.5 text-xs text-muted-foreground/70">{tool.tool_id}</p>
									</div>
									<div class="flex items-center gap-2">
										<span
											class="rounded-full px-2 py-1 text-[10px] font-semibold uppercase {tool.is_enabled
												? 'bg-emerald-500/10 text-emerald-400'
												: 'bg-white/5 text-muted-foreground'}"
										>
											{tool.is_enabled ? 'Enabled' : 'Disabled'}
										</span>
										<button
											onclick={() => configureTool(tool, !tool.is_enabled, tool.config ?? {})}
											disabled={busy}
											class="rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors {tool.is_enabled
												? 'text-red-400 hover:bg-red-400/10'
												: 'text-blue-400 hover:bg-blue-400/10'} disabled:opacity-60"
										>
											{busy ? 'Saving...' : tool.is_enabled ? 'Disable' : 'Enable'}
										</button>
										<button
											onclick={() => {
												expandedConfig = expandedConfig === configKey ? '' : configKey;
											}}
											class="rounded-lg px-3 py-1.5 text-xs font-semibold text-muted-foreground transition-colors hover:bg-white/5 hover:text-foreground"
										>
											Config
										</button>
									</div>
								</div>
								{#if expandedConfig === configKey}
									<div class="mt-4">
										<JsonConfigPanel
											value={JSON.stringify(tool.config ?? {}, null, 2)}
											onSave={(json) => configureTool(tool, tool.is_enabled, parseJsonConfig(json))}
										/>
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{/if}
			</section>
		</div>
	{/if}
	{#if agentUi.test_panel_enabled}
		<aside
			class="flex min-h-[520px] flex-col bg-[var(--surface)] lg:fixed lg:inset-y-0 lg:right-0 lg:z-20 lg:w-[420px]"
		>
			<div
				class="flex h-14 items-center justify-between border-b px-5"
				style="border-color:var(--ds-border)"
			>
				<h2 class="text-sm font-semibold" style="color:var(--text-main)">Test agent</h2>
				<div class="flex items-center gap-1">
					<button
						class="rounded p-1.5 text-muted-foreground transition-colors hover:bg-[var(--surface-hover)] hover:text-foreground"
						aria-label="Test options"
					>
						<MoreHorizontal class="size-4" />
					</button>
					<button
						class="rounded p-1.5 text-muted-foreground transition-colors hover:bg-[var(--surface-hover)] hover:text-foreground"
						aria-label="Close test panel"
					>
						<X class="size-4" />
					</button>
				</div>
			</div>

			<div class="flex flex-1 flex-col justify-end gap-5 p-5">
				<div class="rounded-xl border bg-[var(--canvas)] p-4" style="border-color:var(--ds-border)">
					<div class="flex items-start gap-3">
						<div
							class="flex size-8 shrink-0 items-center justify-center rounded-full bg-blue-500/10 text-blue-500"
						>
							<Bot class="size-4" />
						</div>
						<div class="min-w-0 text-sm leading-relaxed">
							<p class="font-semibold" style="color:var(--text-main)">{instance.name} pronto.</p>
							<p class="mt-1 text-muted-foreground">
								Use este painel para validar instrucoes, guardrails e conhecimento antes de
								publicar.
							</p>
							<ol class="mt-3 list-decimal space-y-1 pl-4 text-xs text-muted-foreground">
								<li>Teste perguntas comuns do tenant.</li>
								<li>Valide respostas com documentos e colecoes.</li>
								<li>Confirme limites definidos nos guardrails.</li>
							</ol>
							<p class="mt-3 text-xs font-semibold" style="color:var(--text-main)">
								O que voce gostaria de investigar primeiro?
							</p>
							<div class="mt-3 flex gap-2 text-muted-foreground">
								<ThumbsUp class="size-4" />
								<ThumbsDown class="size-4" />
							</div>
						</div>
					</div>
				</div>

				<div
					class="rounded-xl border bg-[var(--canvas)] p-3 shadow-sm"
					style="border-color:var(--ds-border)"
				>
					<textarea
						bind:value={testMessage}
						rows="3"
						maxlength="2000"
						placeholder="Faca uma pergunta ou descreva o que precisa"
						class="w-full resize-none bg-transparent text-sm outline-none placeholder:text-muted-foreground"
					></textarea>
					<div class="mt-2 flex items-center justify-between">
						<span class="font-mono text-[10px] text-muted-foreground"
							>{testMessage.length}/2000</span
						>
						<button
							type="button"
							disabled={!testMessage.trim()}
							class="inline-flex size-8 items-center justify-center rounded-md bg-blue-600 text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40"
							aria-label="Send test message"
						>
							<Send class="size-4" />
						</button>
					</div>
				</div>
			</div>
		</aside>
	{/if}
{/if}
