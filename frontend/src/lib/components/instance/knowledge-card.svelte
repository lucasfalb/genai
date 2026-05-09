<script lang="ts">
	import Database from '@lucide/svelte/icons/database';
	import X from '@lucide/svelte/icons/x';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { collectionsApi } from '$lib/api/collections';
	import { getErrorMessage } from '$lib/api/client';
	import { toast } from 'svelte-sonner';
	import ProgressCircle from '$lib/components/ProgressCircle.svelte';
	import KnowledgeDialog from './knowledge-dialog.svelte';
	import * as Accordion from '$lib/components/ui/accordion/index.js';
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import type { DocumentResponse, CollectionResponse } from '$lib/api/types';

	let {
		ragScope = $bindable<string[]>([])
	}: {
		ragScope: string[];
	} = $props();

	let open = $state(false);
	let selectedCollection = $state<CollectionResponse | null>(null);
	let documents = $state<DocumentResponse[]>([]);
	let loadingDocs = $state(false);
	let deleteTarget = $state<DocumentResponse | null>(null);

	let collectionId = $derived(ragScope[0] ?? '');

	$effect(() => {
		if (!collectionId) {
			documents = [];
			selectedCollection = null;
			loadingDocs = false;
			return;
		}
		loadingDocs = true;
		Promise.all([
			collectionsApi.get(collectionId),
			collectionsApi.listDocuments(collectionId)
		])
			.then(([col, docs]) => {
				selectedCollection = col;
				documents = docs;
			})
			.catch(() => {
				documents = [];
				selectedCollection = null;
			})
			.finally(() => {
				loadingDocs = false;
			});
	});

	function onSelect(collectionId: string, _collectionName: string) {
		ragScope = collectionId ? [collectionId] : [];
	}

	function onDialogOpen() {
		open = true;
	}

	async function confirmDelete() {
		if (!deleteTarget || !ragScope[0]) return;
		const target = deleteTarget;
		deleteTarget = null;
		try {
			await collectionsApi.deleteDocument(ragScope[0], target.id);
			documents = documents.filter((d) => d.id !== target.id);
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

	function formatDate(value: string | null): string {
		if (!value) return '\u2014';
		const d = new Date(value);
		return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
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
		<Button variant="outline" onclick={onDialogOpen}>Browse Collections</Button>
	</div>

	{#if ragScope.length > 0 && selectedCollection}
		<div class="flex items-center gap-2 rounded-lg px-4 py-2" style="background:color-mix(in srgb, #3b82f6 8%, transparent);border:1px solid color-mix(in srgb, #3b82f6 20%, transparent)">
			<Database class="size-4 shrink-0 text-blue-400" />
			<span class="flex-1 text-sm font-medium" style="color:var(--text-main)">{selectedCollection.name}</span>
			<button onclick={onDialogOpen} class="rounded px-2 py-0.5 text-[10px] font-semibold text-blue-400 hover:text-blue-300 hover:bg-blue-500/10 transition-colors">
				{selectedCollection.document_count} docs
			</button>
			<Badge variant="outline" class="text-[10px] capitalize">{selectedCollection.indexing_status}</Badge>
			<button onclick={() => { ragScope = []; }} class="rounded p-1 text-muted-foreground hover:text-red-400 hover:bg-red-400/10 transition-colors" aria-label="Remove collection">
				<X class="size-3.5" />
			</button>
		</div>

		{#if loadingDocs}
			<p class="py-3 text-center text-xs text-muted-foreground">Loading documents...</p>
		{:else if documents.length > 0}
			<Accordion.Root type="multiple" class="rounded-lg border" style="border-color:var(--ds-border)">
				{#each documents as doc (doc.id)}
					<Accordion.Item value={doc.id}>
						<Accordion.Trigger class="px-4">
							<div class="flex items-center gap-2 min-w-0 flex-1 mr-2">
								<ProgressCircle status={doc.status} size={12} />
								<span class="truncate font-mono text-xs">{doc.filename}</span>
							</div>
						</Accordion.Trigger>
						<Accordion.Content class="px-4">
							<div class="grid grid-cols-2 gap-2 text-xs pt-1 pb-2">
								<div><span class="text-muted-foreground">Status:</span> <span class="capitalize">{doc.status}</span></div>
								<div><span class="text-muted-foreground">Chunks:</span> {doc.chunk_count}</div>
								<div><span class="text-muted-foreground">Size:</span> {formatBytes(doc.size_bytes)}</div>
								<div><span class="text-muted-foreground">Uploaded:</span> {formatDate(doc.created_at)}</div>
								{#if doc.indexed_at}
									<div><span class="text-muted-foreground">Indexed:</span> {formatDate(doc.indexed_at)}</div>
								{/if}
								{#if doc.error_message}
									<div class="col-span-2"><span class="text-muted-foreground">Error:</span> <span class="text-red-400">{doc.error_message}</span></div>
								{/if}
							</div>
							<div class="flex gap-2 border-t pt-2" style="border-color:var(--ds-border)">
								<Button variant="ghost" size="sm" class="h-7 text-[10px]" onclick={() => (deleteTarget = doc)}>
									<Trash2 class="size-3 mr-1" /> Delete
								</Button>
							</div>
						</Accordion.Content>
					</Accordion.Item>
				{/each}
			</Accordion.Root>
		{:else}
			<p class="py-3 text-center text-xs text-muted-foreground">No documents in this collection.</p>
		{/if}
	{/if}
</div>

<KnowledgeDialog bind:open selectedName={selectedCollection?.name ?? ''} selectedId={ragScope[0] ?? ''} {onSelect} />

<AlertDialog.Root
	open={!!deleteTarget}
	onOpenChange={(o) => { if (!o) deleteTarget = null; }}
>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Delete document</AlertDialog.Title>
			<AlertDialog.Description>
				Delete "{deleteTarget?.filename}"? Indexed chunks will be removed from the vector store.
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>Cancel</AlertDialog.Cancel>
			<AlertDialog.Action onclick={confirmDelete}>Delete</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
