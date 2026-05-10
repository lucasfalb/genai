<script lang="ts">
	import { marked } from 'marked';
	import { collectionsApi } from '$lib/api/collections';
	import { getErrorMessage } from '$lib/api/client';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import type { DocumentResponse } from '$lib/api/types';
	import { toast } from 'svelte-sonner';
	import FilePlus from '@lucide/svelte/icons/file-plus';
	import Save from '@lucide/svelte/icons/save';
	import FileCode from '@lucide/svelte/icons/file-code';
	import Pencil from '@lucide/svelte/icons/pencil';
	import Eye from '@lucide/svelte/icons/eye';

	let {
		open = $bindable(false),
		collectionId,
		document = null,
		onSaved
	}: {
		open: boolean;
		collectionId: string;
		document?: DocumentResponse | null;
		onSaved?: (doc: DocumentResponse) => void;
	} = $props();

	let filename = $state('');
	let content = $state('');
	let saving = $state(false);
	let loading = $state(false);
	let activeTab = $state<'write' | 'preview'>('write');
	const isEdit = $derived(document !== null);

	const isMarkdown = $derived(
		!isEdit || document?.content_type === 'text/markdown'
	);

	// Configure marked
	marked.setOptions({
		breaks: true,
		gfm: true
	});

	const preview = $derived(
		activeTab === 'preview' && content ? marked(content) : ''
	);

	$effect(() => {
		if (open) {
			if (document) {
				filename = document.filename;
				loadContent();
			} else {
				filename = 'untitled.md';
				content = '';
			}
			activeTab = 'write';
		}
	});

	async function loadContent() {
		if (!document) return;
		loading = true;
		try {
			const { blob } = await collectionsApi.fetchDocumentContent(collectionId, document.id);
			content = await blob.text();
		} catch (err) {
			toast.error(getErrorMessage(err, 'Failed to load content.'));
		} finally {
			loading = false;
		}
	}

	async function save() {
		if (!filename.trim()) {
			toast.error('Filename is required.');
			return;
		}
		if (!content.trim()) {
			toast.error('Content is required.');
			return;
		}

		saving = true;
		try {
			let saved: DocumentResponse;

			if (isEdit && document) {
				saved = await collectionsApi.updateDocumentContent(collectionId, document.id, content);
			} else {
				const name = filename.trim();
				const safeName = name.endsWith('.md') || name.endsWith('.txt') ? name : `${name}.md`;
				saved = await collectionsApi.createDocument(collectionId, safeName, content);
			}

			toast.success(isEdit ? 'Document updated.' : 'Document created.');
			onSaved?.(saved);
			open = false;
		} catch (err) {
			toast.error(getErrorMessage(err, isEdit ? 'Update failed.' : 'Create failed.'));
		} finally {
			saving = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if ((e.ctrlKey || e.metaKey) && e.key === 's') {
			e.preventDefault();
			save();
		}
	}

	function insertMarkdown(syntax: string, placeholder = '') {
		const textarea = document.querySelector('.markdown-textarea') as HTMLTextAreaElement;
		if (!textarea) return;

		const start = textarea.selectionStart;
		const end = textarea.selectionEnd;
		const selectedText = content.substring(start, end);
		const textToInsert = selectedText || placeholder;

		const before = content.substring(0, start);
		const after = content.substring(end);

		// Insert markdown syntax
		if (syntax === 'link') {
			content = `${before}[${textToInsert}](url)${after}`;
			setTimeout(() => {
				textarea.focus();
				const urlStart = start + textToInsert.length + 3;
				textarea.setSelectionRange(urlStart, urlStart + 3);
			}, 0);
		} else if (syntax === 'code') {
			content = `${before}\`\`\`\n${textToInsert}\n\`\`\`${after}`;
			setTimeout(() => {
				textarea.focus();
				const newPos = start + 4;
				textarea.setSelectionRange(newPos, newPos + textToInsert.length);
			}, 0);
		} else {
			content = `${before}${syntax}${textToInsert}${syntax}${after}`;
			setTimeout(() => {
				textarea.focus();
				const newPos = start + syntax.length;
				textarea.setSelectionRange(newPos, newPos + textToInsert.length);
			}, 0);
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<Dialog.Root bind:open>
	<Dialog.Content class="flex h-[85vh] w-full max-w-[90vw] flex-col gap-0 p-0">
		<!-- Header -->
		<div class="border-b px-8 py-5" style="border-color:var(--ds-border)">
			<Dialog.Title class="text-xl font-semibold">
				{isEdit ? 'Edit' : 'Create New'} Text Document
			</Dialog.Title>
			<Dialog.Description class="mt-1.5 text-sm">
				{isEdit ? `Editing ${document?.filename ?? ''}` : 'Create a new .md or .txt document with full preview support'}
			</Dialog.Description>
		</div>

		<!-- Content -->
		<div class="flex flex-1 flex-col gap-6 overflow-hidden px-8 py-6">
			<!-- Filename -->
			<div class="grid grid-cols-[1fr_auto] items-end gap-4">
				<div class="space-y-2.5">
					<Label for="filename" class="text-sm font-medium">Document Name</Label>
					<Input
						id="filename"
						bind:value={filename}
						placeholder="e.g., meeting-notes, project-overview"
						disabled={isEdit || saving}
						class="h-11 text-base"
					/>
				</div>
				<div class="flex h-11 items-center gap-2 rounded-md border bg-muted px-4" style="border-color:var(--ds-border)">
					<FileCode class="size-4 text-muted-foreground" />
					<span class="font-mono text-sm">{isEdit && document ? (document.filename.endsWith('.txt') ? '.txt' : '.md') : filename.endsWith('.txt') ? '.txt' : '.md'}</span>
					<span class="text-xs text-muted-foreground">{isMarkdown ? 'Markdown' : 'Plain text'}</span>
				</div>
			</div>

			<!-- Editor Tabs -->
			<Tabs.Root bind:value={activeTab} class="flex flex-1 flex-col overflow-hidden">
				<div class="flex items-center justify-between border-b" style="border-color:var(--ds-border)">
					<Tabs.List class="bg-transparent border-0 p-0">
						<Tabs.Trigger value="write" class="data-[state=active]:border-blue-500 data-[state=active]:text-foreground">
							<Pencil class="size-3.5 mr-1.5" />
							Write
						</Tabs.Trigger>
						<Tabs.Trigger value="preview" class="data-[state=active]:border-blue-500 data-[state=active]:text-foreground">
							<Eye class="size-3.5 mr-1.5" />
							Preview
						</Tabs.Trigger>
					</Tabs.List>

					{#if activeTab === 'write'}
						<div class="flex items-center gap-1 pb-2">
							<Button variant="ghost" size="sm" onclick={() => insertMarkdown('**', 'bold text')} class="h-8 px-2">
								<span class="font-bold text-xs">B</span>
							</Button>
							<Button variant="ghost" size="sm" onclick={() => insertMarkdown('*', 'italic text')} class="h-8 px-2">
								<span class="italic text-xs">I</span>
							</Button>
							<Button variant="ghost" size="sm" onclick={() => insertMarkdown('`', 'code')} class="h-8 px-2">
								<span class="font-mono text-xs">&lt;/&gt;</span>
							</Button>
							<Button variant="ghost" size="sm" onclick={() => insertMarkdown('code')} class="h-8 px-2 font-mono text-xs">
								```
							</Button>
							<Button variant="ghost" size="sm" onclick={() => insertMarkdown('link')} class="h-8 px-2 text-xs">
								Link
							</Button>
						</div>
					{/if}
				</div>

				<Tabs.Content value="write" class="flex-1 overflow-hidden mt-0 data-[state=inactive]:hidden">
					{#if loading}
						<div class="flex h-full items-center justify-center">
							<div class="space-y-3 text-center">
								<Spinner class="mx-auto size-8" />
								<p class="text-sm text-muted-foreground">Loading document...</p>
							</div>
						</div>
					{:else}
						<Textarea
							bind:value={content}
							placeholder="# Start writing your markdown here...&#10;&#10;Use **bold**, *italic*, `code`, and more!"
							class="markdown-textarea h-full w-full resize-none border-0 p-6 font-mono text-sm focus-visible:ring-0"
							disabled={saving}
							style="color:hsl(var(--foreground))"
						/>
					{/if}
				</Tabs.Content>

				<Tabs.Content value="preview" class="flex-1 overflow-auto mt-0 p-6 data-[state=inactive]:hidden">
					{#if content}
						<div class="markdown-preview prose prose-sm max-w-none">
							{@html preview}
						</div>
					{:else}
						<div class="flex h-full items-center justify-center">
							<p class="text-sm text-muted-foreground">Nothing to preview yet. Start writing in the Write tab.</p>
						</div>
					{/if}
				</Tabs.Content>
			</Tabs.Root>
		</div>

		<!-- Footer -->
		<div class="flex items-center justify-between border-t bg-muted/30 px-8 py-5" style="border-color:var(--ds-border)">
			<div class="flex items-center gap-4 text-xs text-muted-foreground">
				<div class="flex items-center gap-1.5">
					<span class="font-medium">Characters:</span>
					<span class="font-mono">{content.length.toLocaleString()}</span>
				</div>
				{#if content}
					<div class="flex items-center gap-1.5">
						<span class="font-medium">Lines:</span>
						<span class="font-mono">{content.split('\n').length.toLocaleString()}</span>
					</div>
					<div class="flex items-center gap-1.5">
						<span class="font-medium">Words:</span>
						<span class="font-mono">{content.split(/\s+/).filter((w) => w.length > 0).length.toLocaleString()}</span>
					</div>
				{/if}
			</div>
			<div class="flex gap-3">
				<Button variant="outline" onclick={() => (open = false)} disabled={saving} size="lg">
					Cancel
				</Button>
				<Button onclick={save} disabled={saving || loading} size="lg" class="min-w-[120px]">
					{#if saving}
						<Spinner data-icon="inline-start" />
						Saving...
					{:else if isEdit}
						<Save data-icon="inline-start" />
						Save Changes
					{:else}
						<FilePlus data-icon="inline-start" />
						Create Document
					{/if}
				</Button>
			</div>
		</div>
	</Dialog.Content>
</Dialog.Root>

<style>
	/* Markdown Preview Styling */
	.markdown-preview {
		color: hsl(var(--foreground)) !important;
		line-height: 1.7;
	}

	.markdown-preview :global(h1),
	.markdown-preview :global(h2),
	.markdown-preview :global(h3),
	.markdown-preview :global(h4),
	.markdown-preview :global(h5),
	.markdown-preview :global(h6) {
		color: hsl(var(--foreground));
		font-weight: 600;
		margin-top: 1.5em;
		margin-bottom: 0.5em;
		line-height: 1.3;
	}

	.markdown-preview :global(h1) {
		font-size: 2em;
		border-bottom: 2px solid var(--ds-border);
		padding-bottom: 0.3em;
	}

	.markdown-preview :global(h2) {
		font-size: 1.5em;
		border-bottom: 1px solid var(--ds-border);
		padding-bottom: 0.3em;
	}

	.markdown-preview :global(h3) {
		font-size: 1.25em;
	}

	.markdown-preview :global(p) {
		color: hsl(var(--foreground));
		margin: 0.5em 0;
	}

	.markdown-preview :global(strong) {
		color: hsl(var(--foreground));
		font-weight: 600;
	}

	.markdown-preview :global(em) {
		color: hsl(var(--foreground));
		font-style: italic;
	}

	.markdown-preview :global(code) {
		color: hsl(var(--foreground));
		background: hsl(var(--muted));
		padding: 0.2em 0.4em;
		border-radius: 3px;
		font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
		font-size: 0.9em;
	}

	.markdown-preview :global(pre) {
		background: hsl(var(--muted));
		border: 1px solid var(--ds-border);
		border-radius: 0.5rem;
		padding: 1rem;
		overflow-x: auto;
		margin: 1em 0;
	}

	.markdown-preview :global(pre code) {
		background: transparent;
		padding: 0;
		font-size: 0.875rem;
		display: block;
	}

	.markdown-preview :global(a) {
		color: rgb(59 130 246);
		text-decoration: underline;
	}

	.markdown-preview :global(a:hover) {
		color: rgb(96 165 250);
	}

	.markdown-preview :global(blockquote) {
		border-left: 3px solid var(--ds-border);
		padding-left: 1rem;
		margin: 1em 0;
		color: hsl(var(--muted-foreground));
		font-style: italic;
	}

	.markdown-preview :global(ul),
	.markdown-preview :global(ol) {
		padding-left: 1.5rem;
		margin: 0.5rem 0;
		color: hsl(var(--foreground));
	}

	.markdown-preview :global(li) {
		color: hsl(var(--foreground));
		margin: 0.25rem 0;
	}

	.markdown-preview :global(table) {
		border-collapse: collapse;
		width: 100%;
		margin: 1rem 0;
	}

	.markdown-preview :global(table th),
	.markdown-preview :global(table td) {
		border: 1px solid var(--ds-border);
		padding: 0.5rem;
		color: hsl(var(--foreground));
	}

	.markdown-preview :global(table th) {
		background: hsl(var(--muted));
		font-weight: 600;
	}

	.markdown-preview :global(table tr:nth-child(even)) {
		background: hsl(var(--muted) / 0.3);
	}

	.markdown-preview :global(hr) {
		border: none;
		border-top: 2px solid var(--ds-border);
		margin: 2em 0;
	}

	.markdown-preview :global(img) {
		max-width: 100%;
		height: auto;
		border-radius: 0.5rem;
		margin: 1em 0;
	}

	/* Tabs styling */
	:global([data-state=active]) {
		border-bottom: 2px solid rgb(59 130 246) !important;
	}
</style>
