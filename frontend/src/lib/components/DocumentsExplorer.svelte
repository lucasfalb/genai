<script lang="ts">
	import { collectionsApi } from '$lib/api/collections';
	import { getErrorMessage } from '$lib/api/client';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import IndexingProgress from '$lib/components/IndexingProgress.svelte';
	import DocumentEditor from '$lib/components/DocumentEditor.svelte';
	import { toast } from 'svelte-sonner';
	import type { DocumentResponse } from '$lib/api/types';
	import Upload from '@lucide/svelte/icons/upload';
	import FileText from '@lucide/svelte/icons/file-text';
	import FilePlus from '@lucide/svelte/icons/file-plus';
	import Pencil from '@lucide/svelte/icons/pencil';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';

	let {
		collectionId,
		initialDocuments = [],
		onChange,
		onPreview
	}: {
		collectionId: string;
		initialDocuments?: DocumentResponse[];
		onChange?: () => void;
		onPreview?: (doc: DocumentResponse) => void;
	} = $props();

	let documents = $state<DocumentResponse[]>(initialDocuments);
	let uploading = $state(false);
	let refreshing = $state(false);
	let deleteTarget = $state<DocumentResponse | null>(null);
	let confirmBulkDelete = $state(false);
	let editorOpen = $state(false);
	let editTarget = $state<DocumentResponse | null>(null);
	let selectedIds = $state<Set<string>>(new Set());
	let deleting = $state(false);
	let fileInput: HTMLInputElement;
	let polling = $state(false);
	let pollTimer: ReturnType<typeof setInterval> | undefined = $state();

	function pendingDocs(): boolean {
		return documents.some((d) => d.status === 'uploaded' || d.status === 'indexing');
	}

	const hasPendingDocs = $derived(pendingDocs());

	$effect(() => {
		// Auto-start polling when there are pending docs
		if (hasPendingDocs && !polling && !pollTimer) {
			pollUntilDone();
		}

		return () => {
			if (pollTimer) clearInterval(pollTimer);
		};
	});

	async function pollUntilDone() {
		if (pollTimer) clearInterval(pollTimer);
		polling = true;
		pollTimer = setInterval(async () => {
			try {
				const updated = await collectionsApi.listDocuments(collectionId);
				documents = updated;
				onChange?.();

				if (!pendingDocs()) {
					clearInterval(pollTimer);
					pollTimer = undefined;
					polling = false;
				}
			} catch {
				clearInterval(pollTimer);
				pollTimer = undefined;
				polling = false;
			}
		}, 1500); // Poll every 1.5 seconds
	}

	const ACCEPT =
		'.pdf,.docx,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown';

	function formatBytes(bytes: number | null): string {
		if (!bytes) return '—';
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
	}

	function formatDate(value: string | null): string {
		if (!value) return '—';
		const d = new Date(value);
		return Number.isNaN(d.getTime()) ? value : d.toLocaleString('pt-BR');
	}

	async function refresh() {
		refreshing = true;
		try {
			documents = await collectionsApi.listDocuments(collectionId);
		} catch (err) {
			toast.error(getErrorMessage(err, 'Refresh failed.'));
		} finally {
			refreshing = false;
		}
	}

	async function handleFiles(files: FileList | null) {
		if (!files || files.length === 0) return;
		uploading = true;
		try {
			for (const file of Array.from(files)) {
				try {
					const created = await collectionsApi.uploadDocument(collectionId, file);
					documents = [created, ...documents];
					toast.success(`Uploaded "${file.name}"`);
				} catch (err) {
					toast.error(`${file.name}: ${getErrorMessage(err, 'Upload failed.')}`);
				}
			}
			onChange?.();
			pollUntilDone();
		} finally {
			uploading = false;
			if (fileInput) fileInput.value = '';
		}
	}

	async function confirmDelete() {
		if (!deleteTarget) return;
		const target = deleteTarget;
		deleteTarget = null;
		try {
			await collectionsApi.deleteDocument(collectionId, target.id);
			documents = documents.filter((d) => d.id !== target.id);
			// Remove from selection if it was selected
			const newSet = new Set(selectedIds);
			newSet.delete(target.id);
			selectedIds = newSet;
			toast.success('Document deleted.');
			onChange?.();
		} catch (err) {
			toast.error(getErrorMessage(err, 'Delete failed.'));
		}
	}

	let dragOver = $state(false);

	function onDrop(e: DragEvent) {
		e.preventDefault();
		dragOver = false;
		handleFiles(e.dataTransfer?.files ?? null);
	}

	function isTextDocument(doc: DocumentResponse): boolean {
		return doc.content_type === 'text/markdown' || doc.content_type === 'text/plain';
	}

	function handleDocumentSaved(doc: DocumentResponse) {
		const index = documents.findIndex((d) => d.id === doc.id);
		if (index >= 0) {
			documents[index] = doc;
		} else {
			documents = [doc, ...documents];
		}
		selectedIds = new Set(); // Clear selection after save
		onChange?.();
		pollUntilDone();
	}

	function openCreateDialog() {
		editTarget = null;
		editorOpen = true;
	}

	function openEditDialog(doc: DocumentResponse) {
		editTarget = doc;
		editorOpen = true;
	}

	const allSelected = $derived(documents.length > 0 && selectedIds.size === documents.length);
	const someSelected = $derived(selectedIds.size > 0 && selectedIds.size < documents.length);

	function toggleAll() {
		if (allSelected) {
			selectedIds = new Set();
		} else {
			selectedIds = new Set(documents.map((d) => d.id));
		}
	}

	function toggleDocument(id: string) {
		const newSet = new Set(selectedIds);
		if (newSet.has(id)) {
			newSet.delete(id);
		} else {
			newSet.add(id);
		}
		selectedIds = newSet;
	}

	async function confirmDeleteSelected() {
		if (selectedIds.size === 0) return;

		const count = selectedIds.size;
		const idsToDelete = Array.from(selectedIds);

		confirmBulkDelete = false;
		deleting = true;
		try {
			for (const id of idsToDelete) {
				await collectionsApi.deleteDocument(collectionId, id);
			}
			documents = documents.filter((d) => !idsToDelete.includes(d.id));
			selectedIds = new Set();
			toast.success(`${count} document(s) deleted.`);
			onChange?.();
		} catch (err) {
			toast.error(getErrorMessage(err, 'Delete failed.'));
		} finally {
			deleting = false;
		}
	}
</script>

<div class="space-y-4">
	<!-- Indexing status banner -->
	{#if hasPendingDocs}
		<div class="rounded-lg border border-yellow-500/20 bg-yellow-500/5 px-4 py-3">
			<div class="flex items-center gap-3">
				<Spinner class="size-4 text-yellow-400" />
				<div class="flex-1">
					<p class="text-sm font-medium text-yellow-400">Indexing in progress</p>
					<p class="mt-0.5 text-xs text-muted-foreground">
						{documents.filter((d) => d.status === 'uploaded' || d.status === 'indexing').length} document(s)
						being processed. Updates every 1.5s.
					</p>
				</div>
			</div>
		</div>
	{/if}

	<!-- Upload zone -->
	<div
		role="region"
		aria-label="Upload area"
		class="flex flex-col items-center gap-3 rounded-lg border-2 border-dashed p-8 text-center transition-colors {dragOver
			? 'border-blue-500 bg-blue-500/5'
			: ''}"
		style="border-color:{dragOver ? '' : 'var(--ds-border)'};background:{dragOver
			? ''
			: 'var(--surface)'}"
		ondragover={(e) => {
			e.preventDefault();
			dragOver = true;
		}}
		ondragleave={() => (dragOver = false)}
		ondrop={onDrop}
	>
		<div class="flex size-12 items-center justify-center rounded-full bg-blue-500/10 text-blue-400">
			<Upload class="size-5" />
		</div>
		<div>
			<p class="text-sm font-semibold" style="color:var(--text-main)">
				Drop files or click to upload
			</p>
			<p class="text-xs text-muted-foreground">PDF, DOCX, TXT, MD up to 50 MB</p>
		</div>
		<input
			bind:this={fileInput}
			type="file"
			multiple
			accept={ACCEPT}
			class="hidden"
			onchange={(e) => handleFiles(e.currentTarget.files)}
		/>
		<Button variant="outline" size="sm" disabled={uploading} onclick={() => fileInput.click()}>
			{#if uploading}<Spinner data-icon="inline-start" />{:else}<Upload
					data-icon="inline-start"
				/>{/if}
			{uploading ? 'Uploading...' : 'Choose files'}
		</Button>
	</div>

	<!-- Documents list -->
	<div class="rounded-lg" style="background:var(--surface);border:1px solid var(--ds-border)">
		<div
			class="flex items-center justify-between border-b px-4 py-3"
			style="border-color:var(--ds-border)"
		>
			<div class="flex items-center gap-3">
				<FileText class="size-4 text-muted-foreground" />
				<p class="text-sm font-semibold" style="color:var(--text-main)">Documents</p>
				<span
					class="rounded-md border px-2 py-0.5 text-[10px] font-semibold"
					style="border-color:var(--ds-border);color:var(--text-muted)">{documents.length}</span
				>
				{#if selectedIds.size > 0}
					<span class="text-xs text-muted-foreground">
						{selectedIds.size} selected
					</span>
				{/if}
			</div>
			<div class="flex gap-2">
				{#if selectedIds.size > 0}
					<Button variant="destructive" size="sm" onclick={() => confirmBulkDelete = true} disabled={deleting}>
						{#if deleting}<Spinner data-icon="inline-start" />{:else}<Trash2
								data-icon="inline-start"
							/>{/if}
						Delete ({selectedIds.size})
					</Button>
				{/if}
				<Button variant="outline" size="sm" onclick={openCreateDialog}>
					<FilePlus data-icon="inline-start" />
					Create file
				</Button>
				<Button variant="ghost" size="sm" disabled={refreshing} onclick={refresh}>
					{#if refreshing}<Spinner data-icon="inline-start" />{:else}<RefreshCw
							data-icon="inline-start"
						/>{/if}
					Refresh
				</Button>
			</div>
		</div>

		{#if documents.length === 0}
			<p class="py-8 text-center text-sm text-muted-foreground">
				No documents yet. Upload one above.
			</p>
		{:else}
			<Table.Root>
				<Table.Header>
					<Table.Row>
						<Table.Head class="w-12">
							<Checkbox
								checked={allSelected}
								indeterminate={someSelected}
								onCheckedChange={toggleAll}
								aria-label="Select all documents"
								class="doc-checkbox border-2"
							/>
						</Table.Head>
						<Table.Head>Filename</Table.Head>
						<Table.Head class="min-w-[220px]">Indexing Status</Table.Head>
						<Table.Head>Size</Table.Head>
						<Table.Head>Uploaded</Table.Head>
						<Table.Head class="w-20"></Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body>
					{#each documents as doc (doc.id)}
						<Table.Row class={selectedIds.has(doc.id) ? 'bg-muted/50' : ''}>
							<Table.Cell>
								<Checkbox
									checked={selectedIds.has(doc.id)}
									onCheckedChange={() => toggleDocument(doc.id)}
									aria-label="Select {doc.filename}"
									class="doc-checkbox border-2"
								/>
							</Table.Cell>
							<Table.Cell class="font-mono text-xs">
								{#if onPreview}
									<button
										class="cursor-pointer text-left hover:underline"
										onclick={(e) => {
											e.stopPropagation();
											onPreview(doc);
										}}
									>
										{doc.filename}
									</button>
								{:else}
									{doc.filename}
								{/if}
							</Table.Cell>
							<Table.Cell>
								<div class="flex flex-col gap-1">
									<IndexingProgress status={doc.status} chunkCount={doc.chunk_count} />
									{#if doc.error_message}
										<p class="line-clamp-2 text-[10px] text-red-400">{doc.error_message}</p>
									{/if}
								</div>
							</Table.Cell>
							<Table.Cell class="text-xs">{formatBytes(doc.size_bytes)}</Table.Cell>
							<Table.Cell class="text-xs text-muted-foreground"
								>{formatDate(doc.created_at)}</Table.Cell
							>
							<Table.Cell>
								<div class="flex gap-1">
									{#if isTextDocument(doc)}
										<Button variant="ghost" size="icon-sm" onclick={() => openEditDialog(doc)}>
											<Pencil />
										</Button>
									{/if}
									<Button variant="ghost" size="icon-sm" onclick={() => (deleteTarget = doc)}>
										<Trash2 />
									</Button>
								</div>
							</Table.Cell>
						</Table.Row>
					{/each}
				</Table.Body>
			</Table.Root>
		{/if}
	</div>
</div>

<DocumentEditor
	bind:open={editorOpen}
	{collectionId}
	document={editTarget}
	onSaved={handleDocumentSaved}
/>

<AlertDialog.Root
	open={!!deleteTarget}
	onOpenChange={(o) => {
		if (!o) deleteTarget = null;
	}}
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

<AlertDialog.Root
	open={confirmBulkDelete}
	onOpenChange={(o) => {
		if (!o) confirmBulkDelete = false;
	}}
>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Delete {selectedIds.size} document(s)</AlertDialog.Title>
			<AlertDialog.Description>
				Delete {selectedIds.size} selected document(s)? All indexed chunks will be removed from the vector store. This action cannot be undone.
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>Cancel</AlertDialog.Cancel>
			<AlertDialog.Action onclick={confirmDeleteSelected}>Delete All</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>

<style>
	:global(.doc-checkbox) {
		/* Better visibility in dark mode */
		background: transparent !important;
		border-color: var(--ds-border) !important;
	}

	:global(.doc-checkbox[data-state='checked']),
	:global(.doc-checkbox[data-state='indeterminate']) {
		background: rgb(59 130 246) !important; /* blue-500 */
		border-color: rgb(59 130 246) !important;
	}

	:global(.doc-checkbox:hover) {
		border-color: rgb(59 130 246) !important;
	}

	:global(.doc-checkbox[data-state='checked']:hover),
	:global(.doc-checkbox[data-state='indeterminate']:hover) {
		background: rgb(96 165 250) !important; /* blue-400 */
	}
</style>
