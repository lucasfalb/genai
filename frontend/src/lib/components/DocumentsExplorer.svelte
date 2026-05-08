<script lang="ts">
	import { collectionsApi } from '$lib/api/collections';
	import { getErrorMessage } from '$lib/api/client';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import { toast } from 'svelte-sonner';
	import type { DocumentResponse } from '$lib/api/types';
	import Upload from '@lucide/svelte/icons/upload';
	import FileText from '@lucide/svelte/icons/file-text';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';

	let {
		collectionId,
		initialDocuments = [],
		onChange
	}: {
		collectionId: string;
		initialDocuments?: DocumentResponse[];
		onChange?: () => void;
	} = $props();

	let documents = $state<DocumentResponse[]>(initialDocuments);
	let uploading = $state(false);
	let refreshing = $state(false);
	let deleteTarget = $state<DocumentResponse | null>(null);
	let fileInput: HTMLInputElement;

	const ACCEPT = '.pdf,.docx,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown';

	function statusVariant(status: string): 'default' | 'secondary' | 'outline' | 'destructive' {
		if (status === 'indexed') return 'default';
		if (status === 'failed') return 'destructive';
		if (status === 'indexing' || status === 'uploaded') return 'secondary';
		return 'outline';
	}

	function formatBytes(bytes: number | null): string {
		if (!bytes) return '—';
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
	}

	function formatDate(value: string | null): string {
		if (!value) return '—';
		const d = new Date(value);
		return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
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
</script>

<div class="space-y-4">
	<!-- Upload zone -->
	<div
		role="region"
		aria-label="Upload area"
		class="flex flex-col items-center gap-3 rounded-xl border-2 border-dashed p-8 text-center transition-colors {dragOver
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
			<p class="text-sm font-semibold" style="color:var(--text-main)">Drop files or click to upload</p>
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
			{#if uploading}<Spinner data-icon="inline-start" />{:else}<Upload data-icon="inline-start" />{/if}
			{uploading ? 'Uploading...' : 'Choose files'}
		</Button>
	</div>

	<!-- Documents list -->
	<div class="rounded-xl" style="background:var(--surface);border:1px solid var(--ds-border)">
		<div class="flex items-center justify-between border-b px-4 py-3" style="border-color:var(--ds-border)">
			<div class="flex items-center gap-2">
				<FileText class="size-4 text-muted-foreground" />
				<p class="text-sm font-semibold" style="color:var(--text-main)">Documents</p>
				<Badge variant="outline">{documents.length}</Badge>
			</div>
			<Button variant="ghost" size="sm" disabled={refreshing} onclick={refresh}>
				{#if refreshing}<Spinner data-icon="inline-start" />{:else}<RefreshCw data-icon="inline-start" />{/if}
				Refresh
			</Button>
		</div>

		{#if documents.length === 0}
			<p class="py-8 text-center text-sm text-muted-foreground">No documents yet. Upload one above.</p>
		{:else}
			<Table.Root>
				<Table.Header>
					<Table.Row>
						<Table.Head>Filename</Table.Head>
						<Table.Head>Status</Table.Head>
						<Table.Head>Chunks</Table.Head>
						<Table.Head>Size</Table.Head>
						<Table.Head>Uploaded</Table.Head>
						<Table.Head class="w-12"></Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body>
					{#each documents as doc (doc.id)}
						<Table.Row>
							<Table.Cell class="font-mono text-xs">{doc.filename}</Table.Cell>
							<Table.Cell>
								<Badge variant={statusVariant(doc.status)}>{doc.status}</Badge>
								{#if doc.error_message}
									<p class="mt-1 text-[10px] text-red-400">{doc.error_message}</p>
								{/if}
							</Table.Cell>
							<Table.Cell class="font-mono text-xs">{doc.chunk_count}</Table.Cell>
							<Table.Cell class="text-xs">{formatBytes(doc.size_bytes)}</Table.Cell>
							<Table.Cell class="text-xs text-muted-foreground">{formatDate(doc.created_at)}</Table.Cell>
							<Table.Cell>
								<Button variant="ghost" size="icon-sm" onclick={() => (deleteTarget = doc)}>
									<Trash2 />
								</Button>
							</Table.Cell>
						</Table.Row>
					{/each}
				</Table.Body>
			</Table.Root>
		{/if}
	</div>
</div>

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
