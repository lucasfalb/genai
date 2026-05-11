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
	import { toast } from 'svelte-sonner';

	let { data } = $props();
	let collection = $state<CollectionResponse>(data.collection);
	let documents = $state<DocumentResponse[]>(data.documents);
	let editOpen = $state(false);
	let deleting = $state(false);
	let reindexing = $state(false);
	let deleteConfirmOpen = $state(false);
	let confirmName = $state('');
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

<div class="mx-auto max-w-5xl space-y-6 p-6">
	<div class="flex items-center justify-between gap-4">
		<div class="flex items-center gap-3">
			<a href="{appBase}/collections" class="rounded-lg p-1.5 transition-colors hover:bg-white/5">
				<ArrowLeft class="size-4 text-muted-foreground" />
			</a>
			<div class="flex size-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
				<Database class="size-5" />
			</div>
			<div>
				<h1 class="font-display text-xl font-semibold" style="color:var(--text-main)">
					{collection.name}
				</h1>
				<p class="mt-1 text-sm text-muted-foreground">
					{collection.description || 'No description.'}
				</p>
			</div>
		</div>
		<div class="flex gap-2">
			{#if collection.document_count > 0}
				<Button variant="outline" disabled={reindexing} onclick={reindexCollection}>
					{#if reindexing}<Spinner data-icon="inline-start" />{:else}<RefreshCw
							data-icon="inline-start"
						/>{/if}
					{reindexing ? 'Queueing...' : 'Reindex'}
				</Button>
			{/if}
			<Button variant="outline" onclick={() => (editOpen = true)}>
				<Pencil data-icon="inline-start" />
				Edit
			</Button>
			<Button variant="destructive" disabled={deleting} onclick={() => (deleteConfirmOpen = true)}>
				{#if deleting}<Spinner data-icon="inline-start" />{:else}<Trash2
						data-icon="inline-start"
					/>{/if}
				{deleting ? 'Deleting...' : 'Delete'}
			</Button>
		</div>
	</div>

	<CollectionDialog
		bind:open={editOpen}
		mode="edit"
		{collection}
		onSaved={(saved) => (collection = saved)}
	/>

	<section class="grid gap-3 md:grid-cols-4">
		<div class="rounded-xl p-4" style="background:var(--surface);border:1px solid var(--ds-border)">
			<p class="text-xs text-muted-foreground">Status</p>
			<div class="mt-2">
				<IndexingStatusBadge
					status={collection.indexing_status}
					progress={collection.indexing_progress}
				/>
			</div>
		</div>
		<div class="rounded-xl p-4" style="background:var(--surface);border:1px solid var(--ds-border)">
			<p class="text-xs text-muted-foreground">Documents</p>
			<p class="mt-2 text-2xl font-semibold">{collection.document_count}</p>
		</div>
		<div class="rounded-xl p-4" style="background:var(--surface);border:1px solid var(--ds-border)">
			<p class="text-xs text-muted-foreground">Indexed</p>
			<div class="flex items-baseline gap-2">
				<p class="mt-2 text-2xl font-semibold text-emerald-400">{collection.indexed_count}</p>
				<!-- {#if collection.document_count > 0}
					<span class="text-xs text-muted-foreground">
						({Math.round((collection.indexed_count / collection.document_count) * 100)}%)
					</span>
				{/if} -->
			</div>
		</div>
		<div class="rounded-xl p-4" style="background:var(--surface);border:1px solid var(--ds-border)">
			<p class="text-xs text-muted-foreground">Failed</p>
			<p class="mt-2 text-2xl font-semibold text-red-400">{collection.failed_count}</p>
		</div>
	</section>

	{#key explorerKey}
		<DocumentsExplorer
			collectionId={collection.id}
			initialDocuments={documents}
			onChange={handleDocumentsChange}
			onPreview={(doc) => (previewTarget = doc)}
		/>
	{/key}

	<FilePreview
		open={previewTarget !== null}
		document={previewTarget}
		onclose={() => (previewTarget = null)}
	/>

	<p class="text-xs text-muted-foreground">
		Last indexed: {formatDate(collection.last_indexed_at)}
	</p>
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
			<AlertDialog.Title class="text-red-400">Delete collection</AlertDialog.Title>
			<AlertDialog.Description>
				This will permanently delete <strong class="text-foreground">"{collection.name}"</strong>
				and all its {collection.document_count} document(s).
				{#if collection.indexed_count > 0}
					<br /><span class="text-amber-400"
						>Indexed data in the vector store will also be removed.</span
					>
				{/if}
				<br />This action <strong class="text-red-400">cannot</strong> be undone.
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
				{#if deleting}<Spinner data-icon="inline-start" />{:else}<Trash2
						data-icon="inline-start"
					/>{/if}
				{deleting ? 'Deleting...' : 'Delete'}
			</Button>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
