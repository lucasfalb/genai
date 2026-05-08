<script lang="ts">
	import Database from '@lucide/svelte/icons/database';
	import X from '@lucide/svelte/icons/x';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { collectionsApi } from '$lib/api/collections';
	import { onMount } from 'svelte';
	import KnowledgeDialog from './knowledge-dialog.svelte';

	let {
		ragScope = $bindable<string[]>([])
	}: {
		ragScope: string[];
	} = $props();

	let open = $state(false);
	let selectedName = $state('');

	onMount(async () => {
		if (ragScope.length > 0) {
			try {
				const col = await collectionsApi.get(ragScope[0]);
				selectedName = col.name;
			} catch { /* name stays empty, no highlight shown */ }
		}
	});

	function onSelect(collectionId: string, collectionName: string) {
		ragScope = collectionId ? [collectionId] : [];
		selectedName = collectionId ? collectionName : '';
	}

	function clearSelection() {
		ragScope = [];
		selectedName = '';
	}
</script>

<div class="rounded-xl p-6 space-y-4" style="background:var(--surface);border:1px solid var(--ds-border)">
	<div class="flex items-center justify-between gap-4">
		<div class="flex items-center gap-3">
			<div class="flex size-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
				<Database class="size-5" />
			</div>
			<div>
				<h2 class="font-display text-sm font-semibold" style="color:var(--text-main)">Knowledge</h2>
				<p class="mt-1 text-sm text-muted-foreground">Select a collection as knowledge base for this agent.</p>
			</div>
		</div>
		<Button variant="outline" onclick={() => (open = true)}>Browse Collections</Button>
	</div>

	{#if ragScope.length > 0 && selectedName}
		<div class="flex items-center gap-2 rounded-lg px-4 py-2" style="background:color-mix(in srgb, #3b82f6 8%, transparent);border:1px solid color-mix(in srgb, #3b82f6 20%, transparent)">
			<Database class="size-4 shrink-0 text-blue-400" />
			<span class="flex-1 text-sm font-medium" style="color:var(--text-main)">{selectedName}</span>
			<Badge variant="outline" class="text-[10px]">knowledge base</Badge>
			<button onclick={clearSelection} class="rounded p-1 text-muted-foreground hover:text-red-400 hover:bg-red-400/10 transition-colors" aria-label="Remove collection">
				<X class="size-3.5" />
			</button>
		</div>
	{/if}
</div>

<KnowledgeDialog bind:open bind:selectedName onSelect={onSelect} selectedId={ragScope[0] ?? ''} />
