<script lang="ts">
	import FileText from '@lucide/svelte/icons/file-text';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { collectionsApi } from '$lib/api/collections';
	import type { DocumentResponse } from '$lib/api/types';

	let {
		open = false,
		document: doc,
		onclose
	}: {
		open: boolean;
		document: DocumentResponse | null;
		onclose?: () => void;
	} = $props();

	let textContent = $state<string | null>(null);
	let pdfUrl = $state<string | null>(null);
	let loading = $state(false);
	let error = $state('');

	$effect(() => {
		if (!open || !doc) return;
		textContent = null;
		pdfUrl = null;
		error = '';
		loadContent();
	});

	async function loadContent() {
		if (!doc) return;
		loading = true;
		try {
			const meta = await collectionsApi.getDocumentContentUrl(doc.collection_id, doc.id);
			const contentType = meta.content_type;
			if (contentType.startsWith('text/')) {
				const res = await fetch(meta.url);
				if (!res.ok) throw new Error('Failed to fetch document content');
				textContent = await res.text();
			} else if (contentType === 'application/pdf') {
				pdfUrl = meta.url;
			} else {
				error = 'Preview not available for this file type.';
			}
		} catch {
			error = 'Failed to load document content.';
		} finally {
			loading = false;
		}
	}

	function handleClose() {
		pdfUrl = null;
		textContent = null;
		error = '';
		onclose?.();
	}

	function formatBytes(bytes: number | null): string {
		if (!bytes) return '\u2014';
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
	}
</script>

<Dialog.Root open={open} onOpenChange={(o) => { if (!o) handleClose(); }}>
	<Dialog.Content class="sm:max-w-4xl max-h-[85vh] overflow-hidden flex flex-col">
		<Dialog.Header>
			<div class="flex items-center gap-3">
				<FileText class="size-5 shrink-0 text-muted-foreground" />
				<div class="min-w-0">
					<Dialog.Title class="truncate text-base">{doc?.filename ?? 'Document'}</Dialog.Title>
					<Dialog.Description class="text-xs">
						{doc ? `${doc.content_type ?? 'Unknown'} \u00b7 ${formatBytes(doc.size_bytes)}` : ''}
					</Dialog.Description>
				</div>
			</div>
		</Dialog.Header>

		<div class="flex-1 overflow-auto min-h-0 px-6 pb-6">
			{#if loading}
				<div class="flex items-center justify-center h-48 text-sm text-muted-foreground">Loading...</div>
			{:else if error}
				<div class="flex items-center justify-center h-48 text-sm text-red-400">{error}</div>
			{:else if textContent !== null}
				<pre class="rounded-lg p-4 text-xs font-mono leading-relaxed whitespace-pre-wrap break-words max-h-[65vh] overflow-auto" style="background:var(--surface);border:1px solid var(--ds-border)">{textContent}</pre>
			{:else if pdfUrl}
				<iframe src={pdfUrl} class="w-full h-[65vh] rounded-lg border-0" title="PDF preview"></iframe>
			{/if}
		</div>
	</Dialog.Content>
</Dialog.Root>
