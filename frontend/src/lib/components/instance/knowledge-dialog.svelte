<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import IndexingStatusBadge from '$lib/components/IndexingStatusBadge.svelte';
	import ProgressCircle from '$lib/components/ProgressCircle.svelte';
	import { collectionsApi } from '$lib/api/collections';
	import { getErrorMessage } from '$lib/api/client';
	import * as Accordion from '$lib/components/ui/accordion/index.js';
	import { toast } from 'svelte-sonner';
	import type { CollectionResponse, DocumentResponse } from '$lib/api/types';
	import Database from '@lucide/svelte/icons/database';
	import FolderPlus from '@lucide/svelte/icons/folder-plus';
	import FileText from '@lucide/svelte/icons/file-text';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Search from '@lucide/svelte/icons/search';
	import Upload from '@lucide/svelte/icons/upload';
	import Trash2 from '@lucide/svelte/icons/trash-2';

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

	// per-collection document state
	let docsByCollection = $state<Record<string, DocumentResponse[]>>({});
	let loadingDocs = $state<Record<string, boolean>>({});
	let uploading = $state<Record<string, boolean>>({});
	let expandedIds = $state<string[]>([]);

	$effect(() => {
		if (open) {
			view = 'list';
			search = '';
			docsByCollection = {};
			loadingDocs = {};
			expandAll = false;
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

	async function loadCollectionDocs(collectionId: string) {
		if (docsByCollection[collectionId]) return;
		loadingDocs = { ...loadingDocs, [collectionId]: true };
		try {
			const docs = await collectionsApi.listDocuments(collectionId);
			docsByCollection = { ...docsByCollection, [collectionId]: docs };
		} catch (err) {
			toast.error(getErrorMessage(err, 'Failed to load documents.'));
		} finally {
			loadingDocs = { ...loadingDocs, [collectionId]: false };
		}
	}

	let expandAll = $state(false);

	function toggleExpandAll() {
		expandAll = !expandAll;
		expandedIds = expandAll ? collections.map((c) => c.id) : [];
	}

	function onAccordionChange(ids: string[]) {
		expandedIds = ids;
		for (const id of ids) {
			loadCollectionDocs(id);
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

	async function handleUpload(collectionId: string) {
		const input = document.createElement('input');
		input.type = 'file';
		input.multiple = true;
		input.accept = '.pdf,.docx,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown';
		input.onchange = async () => {
			const files = input.files;
			if (!files || files.length === 0) return;
			uploading = { ...uploading, [collectionId]: true };
			try {
				for (const file of Array.from(files)) {
					try {
						const created = await collectionsApi.uploadDocument(collectionId, file);
						const existing = docsByCollection[collectionId] ?? [];
						docsByCollection = { ...docsByCollection, [collectionId]: [created, ...existing] };
						toast.success(`Uploaded "${file.name}"`);
					} catch (err) {
						toast.error(`${file.name}: ${getErrorMessage(err, 'Upload failed.')}`);
					}
				}
			} finally {
				uploading = { ...uploading, [collectionId]: false };
			}
		};
		input.click();
	}

	async function deleteDocument(collectionId: string, doc: DocumentResponse) {
		try {
			await collectionsApi.deleteDocument(collectionId, doc.id);
			const existing = docsByCollection[collectionId] ?? [];
			docsByCollection = { ...docsByCollection, [collectionId]: existing.filter((d) => d.id !== doc.id) };
			toast.success('Document deleted.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Delete failed.'));
		}
	}

	function formatBytes(bytes: number | null): string {
		if (!bytes) return '\u2014';
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
	}

	const filtered = $derived(
		search.trim()
			? collections.filter((c) => c.name.toLowerCase().includes(search.toLowerCase()))
			: collections
	);
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-3xl max-h-[85vh] overflow-hidden flex flex-col">
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
							: 'Browse collections and manage documents.'}
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

			<div class="flex-1 overflow-y-auto -mx-6 px-6 py-2">
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
					<div class="flex items-center justify-end py-1">
						<button
							onclick={toggleExpandAll}
							class="text-[11px] text-muted-foreground hover:text-foreground transition-colors"
						>
							{expandAll ? 'Collapse all' : 'Expand all'}
						</button>
					</div>
					<Accordion.Root type="multiple" bind:value={expandedIds} onValueChange={onAccordionChange}>
						{#each filtered as col (col.id)}
							<Accordion.Item value={col.id} class="rounded-lg border mb-2 overflow-hidden" style="border-color:var(--ds-border);background:var(--surface)">
								<Accordion.Trigger class="px-4 py-3 hover:no-underline">
									<div class="flex items-center gap-3 min-w-0 flex-1 mr-2">
										<div class="flex size-8 items-center justify-center rounded-md bg-blue-500/10 text-blue-400 shrink-0">
											<Database class="size-4" />
										</div>
										<div class="min-w-0 flex-1 text-left">
											<div class="flex flex-wrap items-center gap-1.5">
												<span class="text-sm font-semibold" style="color:var(--text-main)">{col.name}</span>
												<IndexingStatusBadge status={col.indexing_status} progress={col.indexing_progress} />
											</div>
											<p class="truncate text-[11px] text-muted-foreground">{col.description || 'No description.'}</p>
										</div>
										<Badge variant="outline" class="font-mono shrink-0">{col.document_count} docs</Badge>
										{#if col.id === selectedId}
											<Badge class="bg-blue-500/10 text-blue-400 border-blue-500/20 shrink-0">Selected</Badge>
										{:else}
											<Button size="sm" variant="outline" class="shrink-0" onclick={(e) => { e.stopPropagation(); onSelect(col.id, col.name); open = false; }}>
												Select
											</Button>
										{/if}
									</div>
								</Accordion.Trigger>
								<Accordion.Content class="px-4 pb-3">
									{#if loadingDocs[col.id]}
										<div class="flex items-center justify-center py-4">
											<Spinner class="size-4" />
										</div>
									{:else if docsByCollection[col.id]?.length}
										<div class="space-y-0.5">
											{#each docsByCollection[col.id] as doc (doc.id)}
												<div class="group flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-white/[0.03] transition-colors">
													<ProgressCircle status={doc.status} size={10} />
													<span class="flex-1 min-w-0 truncate font-mono text-xs" style="color:var(--text-main)">{doc.filename}</span>
													<span class="text-[10px] text-muted-foreground shrink-0">{formatBytes(doc.size_bytes)}</span>
													<span class="text-[10px] capitalize text-muted-foreground shrink-0">{doc.status}</span>
													<button
														onclick={() => deleteDocument(col.id, doc)}
														class="opacity-0 group-hover:opacity-100 rounded p-0.5 text-muted-foreground hover:text-red-400 hover:bg-red-400/10 transition-all"
														aria-label="Delete document"
													>
														<Trash2 class="size-3" />
													</button>
												</div>
											{/each}
										</div>
									{:else}
										<p class="py-2 text-[11px] text-muted-foreground">No documents yet.</p>
									{/if}
									<div class="mt-2">
										<Button variant="ghost" size="sm" class="h-7 text-[11px]" disabled={uploading[col.id]} onclick={() => handleUpload(col.id)}>
											<Upload class="size-3 mr-1" />
											{uploading[col.id] ? 'Uploading...' : 'Upload documents'}
										</Button>
									</div>
								</Accordion.Content>
							</Accordion.Item>
						{/each}
					</Accordion.Root>
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
