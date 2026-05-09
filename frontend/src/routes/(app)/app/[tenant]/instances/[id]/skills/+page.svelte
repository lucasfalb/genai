<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Database from '@lucide/svelte/icons/database';
	import Puzzle from '@lucide/svelte/icons/puzzle';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import JsonConfigPanel from '$lib/components/JsonConfigPanel.svelte';
	import RegistryAddDialog from '$lib/components/instance/registry-add-dialog.svelte';
	import { registryApi } from '$lib/api/registry';
	import { getErrorMessage } from '$lib/api/client';
	import type {
		ToolMetadataResponse,
		SkillActivationResponse,
		ToolActivationResponse
	} from '$lib/api/types';

	let { data } = $props();

	let registryMetadata = $state<ToolMetadataResponse>(data.registryMetadata);
	let registryBusy = $state('');
	let expandedConfig = $state('');
	let addSkillOpen = $state(false);
	let addToolOpen = $state(false);

	async function refreshRegistryMetadata() {
		registryMetadata = await registryApi.getMetadata(data.instance.id);
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

	function parseJsonConfig(json: string): Record<string, unknown> {
		return JSON.parse(json || '{}') as Record<string, unknown>;
	}
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
								<Button variant="ghost" size="sm" onclick={() => (expandedConfig = expandedConfig === key ? '' : key)}>
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
							<div class="mt-4">
								<JsonConfigPanel
									value={JSON.stringify(skill.config ?? {}, null, 2)}
									onSave={(json) => configureSkill(skill, parseJsonConfig(json))}
								/>
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
								<Button variant="ghost" size="sm" onclick={() => (expandedConfig = expandedConfig === key ? '' : key)}>
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
							<div class="mt-4">
								<JsonConfigPanel
									value={JSON.stringify(tool.config ?? {}, null, 2)}
									onSave={(json) => configureTool(tool, parseJsonConfig(json))}
								/>
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
