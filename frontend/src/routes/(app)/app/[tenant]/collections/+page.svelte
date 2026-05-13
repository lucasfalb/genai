<script lang="ts">
	import { page } from '$app/state';
	import CollectionDialog from '$lib/components/CollectionDialog.svelte';
	import IndexingStatusBadge from '$lib/components/IndexingStatusBadge.svelte';
	import type { CollectionResponse } from '$lib/api/types';
	import { tenantBaseFromPath } from '$lib/routes/tenant';
	import Plus from '@lucide/svelte/icons/plus';
	import Search from '@lucide/svelte/icons/search';
	import FileText from '@lucide/svelte/icons/file-text';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import * as Table from '$lib/components/ui/table';

	let { data } = $props();
	let collections = $state<CollectionResponse[]>(
		[...data.collections].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
	);
	let createOpen = $state(false);
	const appBase = $derived(tenantBaseFromPath(page.url.pathname));

	// Search state
	let searchQuery = $state('');

	// Reactive filtered collections
	const filteredCollections = $derived(
		collections.filter((col) => {
			return col.name.toLowerCase().includes(searchQuery.toLowerCase());
		})
	);

	function upsertCollection(collection: CollectionResponse) {
		collections = [collection, ...collections.filter((item) => item.id !== collection.id)].sort(
			(a, b) => Date.parse(b.created_at) - Date.parse(a.created_at)
		);
	}
</script>

<div class="flex flex-col gap-3 p-4">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div class="flex max-w-2xl min-w-[300px] flex-1 items-center gap-3">
			<div class="relative w-full max-w-xs">
				<Search class="absolute top-2.5 left-2.5 h-4 w-4 text-muted-foreground" />
				<Input
					placeholder="Search collections..."
					bind:value={searchQuery}
					class="h-9 bg-background pl-9"
				/>
			</div>
		</div>

		<Button onclick={() => (createOpen = true)} size="sm" class="h-9 gap-2">
			<Plus class="h-4 w-4" />
			New Collection
		</Button>
	</div>

	<CollectionDialog bind:open={createOpen} mode="create" onSaved={upsertCollection} />

	<div class="overflow-hidden border bg-card">
		<Table.Root containerClass="scrollbar-none bg-card" class="w-full table-fixed">
			<Table.Header class="bg-background">
				<Table.Row class="bg-background hover:bg-background">
					<Table.Head
						class="w-[40%] bg-background py-2 text-[11px] font-bold tracking-wider uppercase"
					>
						Collection
					</Table.Head>
					<Table.Head
						class="hidden bg-background py-2 text-center text-[11px] font-bold tracking-wider uppercase md:table-cell"
					>
						Stats
					</Table.Head>
					<Table.Head
						class="w-[120px] bg-background py-2 text-[11px] font-bold tracking-wider uppercase"
					>
						Status
					</Table.Head>
					<Table.Head class="w-[50px] bg-background py-2"></Table.Head>
				</Table.Row>
			</Table.Header>

			<Table.Body>
				{#if filteredCollections.length === 0}
					<Table.Row class="bg-card hover:bg-card">
						<Table.Cell colspan={4} class="h-32 text-center text-muted-foreground">
							<div class="flex flex-col items-center gap-1">
								<span class="text-sm font-medium text-foreground">No collections found</span>
								<span class="text-xs">Try adjusting your search query.</span>
							</div>
						</Table.Cell>
					</Table.Row>
				{:else}
					{#each filteredCollections as collection (collection.id)}
						<Table.Row class="group bg-card transition-colors hover:bg-muted/30">
							<Table.Cell class="py-3">
								<a
									href="{appBase}/collections/{collection.id}"
									class="flex items-center gap-3 overflow-hidden"
								>
									<div
										class="flex h-8 w-8 shrink-0 items-center justify-center border bg-background transition-all group-hover:border-primary/40"
									>
										<FileText class="h-4 w-4 text-muted-foreground group-hover:text-primary" />
									</div>
									<div class="flex min-w-0 flex-col">
										<span class="truncate text-sm font-semibold">{collection.name}</span>
										<span class="truncate text-xs text-muted-foreground"
											>{collection.description || 'No description.'}</span
										>
									</div>
								</a>
							</Table.Cell>

							<Table.Cell class="hidden py-3 md:table-cell">
								<div class="flex justify-center gap-4 text-xs">
									<div class="flex flex-col">
										<span class="text-center font-semibold">{collection.document_count}</span>
										<span class="text-[10px] text-muted-foreground uppercase">Docs</span>
									</div>
									<div class="flex flex-col">
										<span class="text-center font-semibold">{collection.indexed_count}</span>
										<span class="text-[10px] text-muted-foreground uppercase">Indexed</span>
									</div>
									<div class="flex flex-col">
										<span class="text-center font-semibold text-red-400"
											>{collection.failed_count}</span
										>
										<span class="text-[10px] text-muted-foreground uppercase">Failed</span>
									</div>
								</div>
							</Table.Cell>

							<Table.Cell class="py-3">
								<IndexingStatusBadge
									status={collection.indexing_status}
									progress={collection.indexing_progress}
								/>
							</Table.Cell>

							<Table.Cell class="py-3 text-right">
								<Button
									variant="ghost"
									size="icon"
									href="{appBase}/collections/{collection.id}"
									class="h-7 w-7 bg-card text-muted-foreground/30 group-hover:bg-muted group-hover:text-foreground"
								>
									<ChevronRight class="h-4 w-4" />
								</Button>
							</Table.Cell>
						</Table.Row>
					{/each}
				{/if}
			</Table.Body>
		</Table.Root>

		<div class="border-t bg-card px-4 py-2">
			<p class="text-[10px] font-bold tracking-widest text-muted-foreground uppercase">
				Showing {filteredCollections.length} of {collections.length} collections
			</p>
		</div>
	</div>
</div>

<style>
	:global(td) {
		white-space: nowrap;
	}
</style>
