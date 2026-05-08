<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button/index.js';
	import RegistryRow from '$lib/components/instance/registry-row.svelte';
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
		is_enabled = skill.is_enabled,
		config = skill.config ?? {}
	) {
		registryBusy = `skill:${skill.skill_slug}`;
		try {
			await registryApi.activateSkill(data.instance.id, skill.skill_slug, { is_enabled, config });
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
		is_enabled = tool.is_enabled,
		config = tool.config ?? {}
	) {
		registryBusy = `tool:${tool.tool_slug}`;
		try {
			await registryApi.activateToolItem(data.instance.id, tool.tool_slug, { is_enabled, config });
			await refreshRegistryMetadata();
			toast.success('Tool updated.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Tool update failed.'));
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
				{#each registryMetadata.skills as skill (skill.skill_slug)}
					{@const key = `skill:${skill.skill_slug}`}
					<RegistryRow
						slug={skill.skill_slug}
						id={skill.skill_id}
						is_enabled={skill.is_enabled}
						config={skill.config ?? {}}
						busy={registryBusy === key}
						expanded={expandedConfig === key}
						onToggle={() => configureSkill(skill, !skill.is_enabled, skill.config ?? {})}
						onExpandToggle={() => (expandedConfig = expandedConfig === key ? '' : key)}
						onConfigSave={(config) => configureSkill(skill, skill.is_enabled, config)}
					/>
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
				{#each registryMetadata.tools as tool (tool.tool_slug)}
					{@const key = `tool:${tool.tool_slug}`}
					<RegistryRow
						slug={tool.tool_slug}
						id={tool.tool_id}
						is_enabled={tool.is_enabled}
						config={tool.config ?? {}}
						busy={registryBusy === key}
						expanded={expandedConfig === key}
						onToggle={() => configureTool(tool, !tool.is_enabled, tool.config ?? {})}
						onExpandToggle={() => (expandedConfig = expandedConfig === key ? '' : key)}
						onConfigSave={(config) => configureTool(tool, tool.is_enabled, config)}
					/>
				{/each}
			</div>
		{/if}
	</section>
</div>

<RegistryAddDialog
	bind:open={addSkillOpen}
	kind="skill"
	excludeSlugs={registryMetadata.skills.map((s) => s.skill_slug)}
	onPick={addSkill}
/>

<RegistryAddDialog
	bind:open={addToolOpen}
	kind="tool"
	excludeSlugs={registryMetadata.tools.map((t) => t.tool_slug)}
	onPick={addTool}
/>
