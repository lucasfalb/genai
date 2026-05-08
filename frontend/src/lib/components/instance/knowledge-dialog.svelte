<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import IndexingStatusBadge from '$lib/components/IndexingStatusBadge.svelte';
	import { collectionsApi } from '$lib/api/collections';
	import { getErrorMessage } from '$lib/api/client';
	import { toast } from 'svelte-sonner';
	import type { CollectionResponse } from '$lib/api/types';
	import Database from '@lucide/svelte/icons/database';
	import FolderPlus from '@lucide/svelte/icons/folder-plus';
	import FileText from '@lucide/svelte/icons/file-text';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Search from '@lucide/svelte/icons/search';

	let {
		open = $bindable(false),
		selectedName = $bindable(''),
		selectedId = '',
		onSelect
	}: {
		open: boolean;
		selectedName: string;
		selectedId: string;
		onSelect: (id: string, name: string) => void;
	} = $props();

	let collections = $state<CollectionResponse[]>([]);
	let loading = $state(false);
	let view = $state<'list' | 'create'>('list');
	let search = $state('');

	let newName = $state('');
	let newDescription = $state('');
	let creating = $state(false);

	$effect(() => {
		if (open) {
			view = 'list';
			search = '';
			loadCollections();
		}
	});

	async function loadCollections() {
		loading = true;
		try {
			collections = (await collectionsApi.list()).sort(
				(a, b) => Date.parse(b.created_at) - Date.parse(a.created_at)
			);
		} catch (err) {
			toast.error(getErrorMessage(err, 'Failed to load collections.'));
		} finally {
			loading = false;
		}
	}

	async function createCollection() {
		if (newName.trim().length < 2) {
			toast.error('Name must have at least 2 characters.');
			return;
		}
		creating = true;
		try {
			const created = await collectionsApi.create({
				name: newName.trim(),
				description: newDescription.trim() || undefined
			});
			collections = [created, ...collections];
			newName = '';
			newDescription = '';
			view = 'list';
			toast.success('Collection created.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Create failed.'));
		} finally {
			creating = false;
		}
	}

	const filtered = $derived(
		search.trim()
			? collections.filter((c) => c.name.toLowerCase().includes(search.toLowerCase()))
			: collections
	);
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
		<Dialog.Header>
			<div class="flex items-center gap-2">
				{#if view === 'create'}
					<Button variant="ghost" size="icon-sm" onclick={() => (view = 'list')}>
						<ArrowLeft />
					</Button>
				{:else}
					<div class="flex size-8 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
						<Database class="size-4" />
					</div>
				{/if}
				<div class="flex-1">
					<Dialog.Title>{view === 'create' ? 'New Collection' : 'Knowledge Explorer'}</Dialog.Title>
					<Dialog.Description>
						{view === 'create'
							? 'Group documents for agent retrieval.'
							: 'Manage collections used by this agent.'}
					</Dialog.Description>
				</div>
			</div>
		</Dialog.Header>

		{#if view === 'list'}
			<div class="flex items-center gap-2 border-y px-1 py-2" style="border-color:var(--ds-border)">
				<Search class="size-4 text-muted-foreground ml-2" />
				<input
					bind:value={search}
					placeholder="Search collections..."
					class="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
				/>
				<Button size="sm" onclick={() => (view = 'create')}>
					<FolderPlus data-icon="inline-start" />
					New
				</Button>
			</div>

			<div class="flex-1 overflow-y-auto -mx-6 px-6">
				{#if loading}
					<div class="flex items-center justify-center py-12">
						<Spinner />
					</div>
				{:else if filtered.length === 0}
					<div class="flex flex-col items-center gap-2 py-12 text-center">
						<FileText class="size-8 text-muted-foreground/40" />
						<p class="text-sm text-muted-foreground">
							{search ? 'No matches.' : 'No collections yet.'}
						</p>
					</div>
				{:else}
					<ul class="divide-y" style="border-color:var(--ds-border)">
						{#each filtered as col (col.id)}
							{@const isSelected = col.id === selectedId}
							<li
								class="flex items-center gap-3 py-3 {isSelected ? 'rounded-lg bg-blue-500/5 -mx-2 px-2' : ''}"
								style={isSelected ? 'border-color:color-mix(in srgb, #3b82f6 20%, transparent)' : ''}
							>
								<div class="flex size-9 items-center justify-center rounded-md bg-blue-500/10 text-blue-400">
									<Database class="size-4" />
								</div>
								<div class="min-w-0 flex-1">
									<div class="flex flex-wrap items-center gap-2">
										<p class="truncate text-sm font-semibold" style="color:var(--text-main)">{col.name}</p>
										<IndexingStatusBadge status={col.indexing_status} progress={col.indexing_progress} />
									</div>
									<p class="line-clamp-1 text-xs text-muted-foreground">{col.description || 'No description.'}</p>
								</div>
								<Badge variant="outline" class="font-mono">{col.document_count} docs</Badge>
								{#if isSelected}
									<Badge class="bg-blue-500/10 text-blue-400 border-blue-500/20">Selected</Badge>
								{:else}
									<Button size="sm" variant="outline" onclick={() => { onSelect(col.id, col.name); open = false; }}>
										Select
									</Button>
								{/if}
							</li>
						{/each}
					</ul>
				{/if}
			</div>

			<Dialog.Footer>
				<Button variant="ghost" onclick={() => (open = false)}>Close</Button>
			</Dialog.Footer>
		{:else}
			<div class="flex-1 space-y-4 py-2">
				<div class="space-y-1.5">
					<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Name *</label>
					<Input bind:value={newName} placeholder="Product docs" />
				</div>
				<div class="space-y-1.5">
					<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Description</label>
					<Input bind:value={newDescription} placeholder="Optional description" />
				</div>
			</div>

			<Dialog.Footer>
				<Button variant="ghost" onclick={() => (view = 'list')}>Cancel</Button>
				<Button disabled={creating} onclick={createCollection}>
					{#if creating}<Spinner data-icon="inline-start" />{/if}
					{creating ? 'Creating...' : 'Create Collection'}
				</Button>
			</Dialog.Footer>
		{/if}
	</Dialog.Content>
</Dialog.Root>
