<script lang="ts">
	import { page } from '$app/state';
	import CollectionDialog from '$lib/components/CollectionDialog.svelte';
	import IndexingStatusBadge from '$lib/components/IndexingStatusBadge.svelte';
	import type { CollectionResponse } from '$lib/api/types';
	import { tenantBaseFromPath } from '$lib/routes/tenant';
	import Database from '@lucide/svelte/icons/database';
	import Plus from '@lucide/svelte/icons/plus';
	import FileText from '@lucide/svelte/icons/file-text';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';

	let { data } = $props();
	let collections = $state<CollectionResponse[]>(
		[...data.collections].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
	);
	let createOpen = $state(false);
	const appBase = $derived(tenantBaseFromPath(page.url.pathname));

	function upsertCollection(collection: CollectionResponse) {
		collections = [collection, ...collections.filter((item) => item.id !== collection.id)].sort(
			(a, b) => Date.parse(b.created_at) - Date.parse(a.created_at)
		);
	}
</script>

<div class="mx-auto max-w-6xl space-y-6 p-6">
	<div class="flex items-center justify-between gap-4">
		<div class="flex items-center gap-3">
			<div class="flex size-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
				<Database class="size-5" />
			</div>
			<div>
				<h1 class="font-display text-xl font-semibold" style="color:var(--text-main)">Collections</h1>
				<p class="mt-1 text-sm text-muted-foreground">Document groups used by agent knowledge retrieval.</p>
			</div>
		</div>
		<button
			onclick={() => (createOpen = true)}
			class="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500"
		>
			<Plus class="size-4" />
			New Collection
		</button>
	</div>

	<CollectionDialog bind:open={createOpen} mode="create" onSaved={upsertCollection} />

	{#if collections.length === 0}
		<section class="flex flex-col items-center gap-4 rounded-xl py-16 text-center" style="background:var(--surface);border:1px solid var(--ds-border)">
			<div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-500/10 text-blue-400">
				<FileText class="h-7 w-7" />
			</div>
			<div>
				<p class="font-display font-semibold" style="color:var(--text-main)">No collections yet</p>
				<p class="mt-1 text-sm text-muted-foreground">Create a collection before uploading documents.</p>
			</div>
		</section>
	{:else}
		<div class="grid gap-3">
			{#each collections as collection (collection.id)}
				<a
					href="{appBase}/collections/{collection.id}"
					class="group rounded-xl p-4 transition-colors hover:bg-white/[0.03]"
					style="background:var(--surface);border:1px solid var(--ds-border)"
				>
					<div class="flex items-center gap-4">
						<div class="min-w-0 flex-1">
							<div class="flex flex-wrap items-center gap-2">
								<h2 class="truncate text-sm font-semibold" style="color:var(--text-main)">{collection.name}</h2>
								<IndexingStatusBadge status={collection.indexing_status} progress={collection.indexing_progress} />
							</div>
							<p class="mt-1 line-clamp-2 text-sm text-muted-foreground">{collection.description || 'No description.'}</p>
						</div>
						<div class="hidden grid-cols-3 gap-4 text-center text-xs md:grid">
							<div><p class="font-semibold">{collection.document_count}</p><p class="text-muted-foreground">Docs</p></div>
							<div><p class="font-semibold">{collection.indexed_count}</p><p class="text-muted-foreground">Indexed</p></div>
							<div><p class="font-semibold text-red-400">{collection.failed_count}</p><p class="text-muted-foreground">Failed</p></div>
						</div>
						<ChevronRight class="size-4 text-muted-foreground/50 transition-transform group-hover:translate-x-0.5" />
					</div>
				</a>
			{/each}
		</div>
	{/if}
</div>
