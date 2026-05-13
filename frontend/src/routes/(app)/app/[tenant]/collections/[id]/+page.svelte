<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import CollectionDialog from '$lib/components/CollectionDialog.svelte';
	import IndexingStatusBadge from '$lib/components/IndexingStatusBadge.svelte';
	import DocumentsExplorer from '$lib/components/DocumentsExplorer.svelte';
	import { collectionsApi } from '$lib/api/collections';
	import { getErrorMessage } from '$lib/api/client';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import type { CollectionResponse, DocumentResponse } from '$lib/api/types';
	import { tenantBaseFromPath } from '$lib/routes/tenant';
	import FilePreview from '$lib/components/FilePreview.svelte';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Database from '@lucide/svelte/icons/database';
	import Pencil from '@lucide/svelte/icons/pencil';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Search from '@lucide/svelte/icons/search';
	import { toast } from 'svelte-sonner';

	let { data } = $props();
	let collection = $state<CollectionResponse>(data.collection);
	let documents = $state<DocumentResponse[]>(data.documents);
	let editOpen = $state(false);
	let deleting = $state(false);
	let reindexing = $state(false);
	let deleteConfirmOpen = $state(false);
	let confirmName = $state('');
	let searchQuery = $state('');

	const canDelete = $derived(confirmName === collection.name);
	const appBase = $derived(tenantBaseFromPath(page.url.pathname));
	let previewTarget = $state<DocumentResponse | null>(null);
	let explorerKey = $state(0);

	async function refreshCollection() {
		try {
			collection = await collectionsApi.get(collection.id);
		} catch {
			// silent
		}
	}

	function handleDocumentsChange() {
		refreshCollection();
	}

	function formatDate(value: string | null): string {
		if (!value) return '—';
		const date = new Date(value);
		return Number.isNaN(date.getTime()) ? value : date.toLocaleString('pt-BR');
	}

	async function deleteCollection() {
		deleting = true;
		deleteConfirmOpen = false;
		try {
			await collectionsApi.delete(collection.id);
			toast.success('Collection deleted.');
			await goto(`${appBase}/collections`);
		} catch (err) {
			toast.error(getErrorMessage(err, 'Collection delete failed.'));
		} finally {
			deleting = false;
		}
	}

	async function reindexCollection() {
		reindexing = true;
		try {
			collection = await collectionsApi.reindex(collection.id);
			const updated = await collectionsApi.listDocuments(collection.id);
			documents = updated;
			explorerKey++; // Force re-render DocumentsExplorer
			toast.success('Reindex queued.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Reindex failed.'));
		} finally {
			reindexing = false;
		}
	}
</script>

<div class="flex flex-col gap-6 p-4">
	<!-- Header -->
	<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
		<div class="flex items-center gap-3">
			<Button
				variant="ghost"
				size="icon"
				href="{appBase}/collections"
				class="h-8 w-8 text-muted-foreground"
			>
				<ArrowLeft class="size-4" />
			</Button>
			<div class="flex size-10 items-center justify-center border bg-card text-blue-400">
				<Database class="size-5" />
			</div>
			<div class="flex flex-col overflow-hidden">
				<h1 class="truncate font-display text-xl font-semibold">
					{collection.name}
				</h1>
				<p class="truncate text-sm text-muted-foreground">
					{collection.description || 'No description.'}
				</p>
			</div>
		</div>

		<div class="flex flex-wrap items-center gap-2">
			{#if collection.document_count > 0}
				<Button
					variant="outline"
					size="sm"
					class="h-9 gap-2"
					disabled={reindexing}
					onclick={reindexCollection}
				>
					{#if reindexing}<Spinner class="size-3.5" />{:else}<RefreshCw class="size-3.5" />{/if}
					Reindex
				</Button>
			{/if}
			<Button variant="outline" size="sm" class="h-9 gap-2" onclick={() => (editOpen = true)}>
				<Pencil class="size-3.5" />
				Edit
			</Button>
			<Button
				variant="destructive"
				size="sm"
				class="h-9 gap-2"
				disabled={deleting}
				onclick={() => (deleteConfirmOpen = true)}
			>
				{#if deleting}<Spinner class="size-3.5" />{:else}<Trash2 class="size-3.5" />{/if}
				Delete
			</Button>
		</div>
	</div>

	<!-- Stats Grid -->
	<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
		<div class="flex flex-col gap-1 border bg-card p-4">
			<span class="text-[10px] font-bold tracking-widest text-muted-foreground uppercase"
				>Status</span
			>
			<div class="mt-1">
				<IndexingStatusBadge
					status={collection.indexing_status}
					progress={collection.indexing_progress}
				/>
			</div>
		</div>
		<div class="flex flex-col gap-1 border bg-card p-4">
			<span class="text-[10px] font-bold tracking-widest text-muted-foreground uppercase"
				>Documents</span
			>
			<span class="text-2xl font-bold">{collection.document_count}</span>
		</div>
		<div class="flex flex-col gap-1 border bg-card p-4">
			<span class="text-[10px] font-bold tracking-widest text-muted-foreground uppercase"
				>Indexed</span
			>
			<div class="flex items-baseline gap-2">
				<span class="text-2xl font-bold text-emerald-500">{collection.indexed_count}</span>
				{#if collection.document_count > 0}
					<span class="text-xs font-medium text-muted-foreground">
						({Math.round((collection.indexed_count / collection.document_count) * 100)}%)
					</span>
				{/if}
			</div>
		</div>
		<div class="flex flex-col gap-1 border bg-card p-4">
			<span class="text-[10px] font-bold tracking-widest text-muted-foreground uppercase"
				>Failed</span
			>
			<span class="text-2xl font-bold text-red-500">{collection.failed_count}</span>
		</div>
	</div>

	<!-- Documents Explorer Section -->
	<div class="flex flex-col gap-4">
		{#key explorerKey}
			<DocumentsExplorer
				collectionId={collection.id}
				initialDocuments={documents}
				bind:searchQuery
				onChange={handleDocumentsChange}
				onPreview={(doc) => (previewTarget = doc)}
			/>
		{/key}
	</div>

	<CollectionDialog
		bind:open={editOpen}
		mode="edit"
		{collection}
		onSaved={(saved) => (collection = saved)}
	/>

	<FilePreview
		open={previewTarget !== null}
		document={previewTarget}
		onclose={() => (previewTarget = null)}
	/>

	<div class="flex items-center justify-between border-t pt-4">
		<p class="text-[10px] font-bold tracking-widest text-muted-foreground uppercase">
			Last indexed: {formatDate(collection.last_indexed_at)}
		</p>
	</div>
</div>

<AlertDialog.Root
	open={deleteConfirmOpen}
	onOpenChange={(o) => {
		if (!o) {
			deleteConfirmOpen = false;
			confirmName = '';
		}
	}}
>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title class="text-red-500">Delete collection</AlertDialog.Title>
			<AlertDialog.Description>
				This will permanently delete <strong class="text-foreground">"{collection.name}"</strong>
				and all its {collection.document_count} document(s).
				{#if collection.indexed_count > 0}
					<br /><span class="text-amber-500"
						>Indexed data in the vector store will also be removed.</span
					>
				{/if}
				<br />This action <strong class="text-red-500">cannot</strong> be undone.
			</AlertDialog.Description>
		</AlertDialog.Header>
		<div class="px-6 pb-4">
			<label class="mb-1.5 block text-xs text-muted-foreground">
				Type <span class="font-mono font-semibold text-foreground">{collection.name}</span> to confirm:
			</label>
			<Input
				bind:value={confirmName}
				placeholder={collection.name}
				onkeydown={(e) => {
					if (e.key === 'Enter' && canDelete) deleteCollection();
				}}
			/>
		</div>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>Cancel</AlertDialog.Cancel>
			<Button variant="destructive" disabled={!canDelete || deleting} onclick={deleteCollection}>
				{#if deleting}<Spinner class="size-3.5" />{:else}<Trash2 class="size-3.5" />{/if}
				Delete
			</Button>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
