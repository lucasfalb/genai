<script lang="ts">
	import Save from '@lucide/svelte/icons/save';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { toast } from 'svelte-sonner';
	import DetailsCard from '$lib/components/instance/details-card.svelte';
	import CorePromptCard from '$lib/components/instance/core-prompt-card.svelte';
	import KnowledgeCard from '$lib/components/instance/knowledge-card.svelte';
	import { instancesApi } from '$lib/api/instances';
	import { getErrorMessage } from '$lib/api/client';
	import { tenantBaseFromPath } from '$lib/routes/tenant';
	import { getAgentUiSettings } from '$lib/settings/agent-ui';
	import { page } from '$app/state';
	import type { AgentInstanceResponse } from '$lib/api/types';

	let { data } = $props();

	const appBase = $derived(tenantBaseFromPath(page.url.pathname));
	const agentUi = getAgentUiSettings(data.publicSettings);

	let instance = $state<AgentInstanceResponse>(data.instance);
	let name = $state(data.instance.name);
	let description = $state(data.instance.description ?? '');
	let core_prompt = $state(data.instance.core_prompt);
	let model = $state(data.instance.model);
	let temperature = $state(data.instance.temperature);
	let rag_scope = $state(data.instance.rag_scope ?? 'none');
	let saving = $state(false);
	let validationError = $state('');

	const MODELS = agentUi.models.map((item) => item.value);

	async function saveConfig() {
		validationError = '';
		if (!name.trim()) { validationError = 'Name is required.'; return; }
		if (!core_prompt.trim()) { validationError = 'Core prompt is required.'; return; }
		if (temperature < 0 || temperature > 2) { validationError = 'Temperature must be between 0 and 2.'; return; }
		saving = true;
		try {
			instance = await instancesApi.update(instance.id, {
				name: name.trim(),
				description: description.trim() || undefined,
				core_prompt: core_prompt.trim(),
				model,
				temperature,
				rag_scope: rag_scope === 'none' ? undefined : rag_scope
			});
			toast.success('Agent saved.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Save failed.'));
		} finally {
			saving = false;
		}
	}
</script>

<div class="mx-auto max-w-5xl space-y-5 px-6 py-5">
	{#if validationError}
		<div class="rounded-xl px-4 py-3 text-sm text-red-400" style="background:color-mix(in srgb,red 8%,transparent);border:1px solid color-mix(in srgb,red 18%,transparent)">{validationError}</div>
	{/if}

	<DetailsCard
		bind:name
		bind:description
		bind:model
		bind:temperature
		bind:rag_scope
		status={instance.status}
		models={MODELS}
	/>

	<CorePromptCard bind:core_prompt />

	<KnowledgeCard collectionsBaseHref="{appBase}/collections" />

	<div class="flex justify-end">
		<Button onclick={saveConfig} disabled={saving}>
			{#if saving}<Spinner data-icon="inline-start" />{:else}<Save data-icon="inline-start" />{/if}
			{saving ? 'Saving...' : 'Save changes'}
		</Button>
	</div>
</div>
