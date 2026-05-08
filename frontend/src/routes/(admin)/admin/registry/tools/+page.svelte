<script lang="ts">
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import { superadminApi } from '$lib/api/superadmin';
	import { getErrorMessage } from '$lib/api/client';
	import type { ToolDefinitionResponse } from '$lib/api/types';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import * as Sheet from '$lib/components/ui/sheet/index.js';
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import Wrench from '@lucide/svelte/icons/wrench';
	import Plus from '@lucide/svelte/icons/plus';
	import Trash2 from '@lucide/svelte/icons/trash-2';

	let { data } = $props();

	let tools = $state<ToolDefinitionResponse[]>(data.tools);
	let sheetMode = $state<'create' | 'edit' | null>(null);
	let busy = $state(false);
	let deleteTarget = $state<ToolDefinitionResponse | null>(null);

	// Shared form fields
	let formSlug = $state('');
	let formName = $state('');
	let formDescription = $state('');
	let formCategory = $state('');
	let formPromptBlock = $state('');
	let formExecutor = $state('');
	let formIsBuiltin = $state(false);
	let formSchema = $state('{}');

	let editingTool = $state<ToolDefinitionResponse | null>(null);

	const sheetOpen = $derived(sheetMode !== null);

	function openCreate() {
		formSlug = '';
		formName = '';
		formDescription = '';
		formCategory = '';
		formPromptBlock = '';
		formExecutor = '';
		formIsBuiltin = false;
		formSchema = '{}';
		editingTool = null;
		sheetMode = 'create';
	}

	function openEdit(t: ToolDefinitionResponse) {
		editingTool = t;
		formSlug = t.slug;
		formName = t.name;
		formDescription = t.description ?? '';
		formCategory = t.category ?? '';
		formPromptBlock = t.prompt_block ?? '';
		formExecutor = t.executor ?? '';
		formIsBuiltin = t.is_builtin ?? false;
		formSchema = JSON.stringify(t.schema ?? {}, null, 2);
		sheetMode = 'edit';
	}

	async function save() {
		let schema: Record<string, unknown> = {};
		try {
			schema = JSON.parse(formSchema || '{}');
		} catch {
			toast.error('Schema JSON is invalid.');
			return;
		}

		if (sheetMode === 'create') {
			if (!formSlug.trim() || !formName.trim()) {
				toast.error('Slug and name are required.');
				return;
			}
			busy = true;
			try {
				const created = await superadminApi.saveTool(formSlug.trim(), {
					slug: formSlug.trim(),
					name: formName.trim(),
					description: formDescription.trim(),
					category: formCategory.trim(),
					prompt_block: formPromptBlock,
					executor: formExecutor.trim(),
					is_builtin: formIsBuiltin,
					schema
				});
				tools = [...tools, created];
				sheetMode = null;
				toast.success('Tool created.');
			} catch (err) {
				toast.error(getErrorMessage(err, 'Create failed.'));
			} finally {
				busy = false;
			}
		} else if (sheetMode === 'edit' && editingTool) {
			busy = true;
			try {
				const updated = await superadminApi.saveTool(editingTool.slug, {
					slug: editingTool.slug,
					name: formName.trim(),
					description: formDescription.trim(),
					category: formCategory.trim(),
					prompt_block: formPromptBlock,
					executor: formExecutor.trim(),
					is_builtin: formIsBuiltin,
					schema
				});
				tools = tools.map((t) => (t.slug === updated.slug ? updated : t));
				editingTool = updated;
				sheetMode = null;
				toast.success('Tool saved.');
			} catch (err) {
				toast.error(getErrorMessage(err, 'Save failed.'));
			} finally {
				busy = false;
			}
		}
	}

	async function confirmDelete() {
		if (!deleteTarget) return;
		const target = deleteTarget;
		deleteTarget = null;
		busy = true;
		try {
			await superadminApi.deleteTool(target.slug);
			tools = tools.filter((t) => t.slug !== target.slug);
			sheetMode = null;
			toast.success('Tool deleted.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Delete failed.'));
		} finally {
			busy = false;
		}
	}
</script>

<div class="flex flex-col gap-6 p-6">
	<div class="flex items-center justify-between gap-3">
		<div class="flex items-center gap-3">
			<div class="flex size-9 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
				<Wrench class="size-4" />
			</div>
			<div>
				<h1 class="font-display text-lg font-semibold">Tools</h1>
				<p class="text-xs text-muted-foreground">{tools.length} global tool definitions</p>
			</div>
		</div>
		<Button onclick={openCreate}>
			<Plus data-icon="inline-start" />
			New Tool
		</Button>
	</div>

	<!-- Create / Edit Sheet -->
	<Sheet.Root
		open={sheetOpen}
		onOpenChange={(o) => {
			if (!o) sheetMode = null;
		}}
	>
		<Sheet.Content side="right" class="w-120 sm:max-w-none overflow-y-auto">
			<Sheet.Header>
				<Sheet.Title>{sheetMode === 'create' ? 'New Tool' : `Edit ${editingTool?.slug}`}</Sheet.Title>
				{#if sheetMode === 'create'}
					<p class="text-xs text-muted-foreground">Slug cannot be changed after creation.</p>
				{:else}
					<p class="text-xs text-muted-foreground">Slug is immutable.</p>
				{/if}
			</Sheet.Header>

			<div class="flex flex-col gap-4 py-4">
				{#if sheetMode === 'create'}
					<div class="flex flex-col gap-1.5">
						<label class="text-sm font-medium">Slug</label>
						<Input bind:value={formSlug} placeholder="my-tool" class="font-mono" />
					</div>
				{/if}

				<div class="grid grid-cols-2 gap-4">
					<div class="flex flex-col gap-1.5">
						<label class="text-sm font-medium">Name</label>
						<Input bind:value={formName} />
					</div>
					<div class="flex flex-col gap-1.5">
						<label class="text-sm font-medium">Category</label>
						<Input bind:value={formCategory} />
					</div>
					<div class="col-span-2 flex flex-col gap-1.5">
						<label class="text-sm font-medium">Description</label>
						<Input bind:value={formDescription} />
					</div>
					<div class="flex flex-col gap-1.5">
						<label class="text-sm font-medium">Executor</label>
						<Input bind:value={formExecutor} class="font-mono" />
					</div>
					<div class="flex items-center justify-between rounded-lg border px-3 py-2">
						<p class="text-sm font-medium">Builtin</p>
						<Switch bind:checked={formIsBuiltin} />
					</div>
				</div>

				<div class="flex flex-col gap-1.5">
					<label class="text-sm font-medium">Prompt Block</label>
					<Textarea bind:value={formPromptBlock} rows={4} class="font-mono text-xs" />
				</div>

				<div class="flex flex-col gap-1.5">
					<label class="text-sm font-medium">Schema JSON</label>
					<Textarea bind:value={formSchema} rows={6} class="font-mono text-xs" />
				</div>
			</div>

			<Sheet.Footer>
				{#if sheetMode === 'edit' && editingTool}
					<Button
						variant="destructive"
						onclick={() => (deleteTarget = editingTool)}
						disabled={busy}
					>
						<Trash2 data-icon="inline-start" />
						Delete
					</Button>
				{/if}
				<Button variant="ghost" onclick={() => (sheetMode = null)}>Cancel</Button>
				<Button disabled={busy} onclick={save}>
					{#if busy}<Spinner data-icon="inline-start" />{/if}
					{#if busy}
						{sheetMode === 'create' ? 'Creating...' : 'Saving...'}
					{:else}
						{sheetMode === 'create' ? 'Create Tool' : 'Save Tool'}
					{/if}
				</Button>
			</Sheet.Footer>
		</Sheet.Content>
	</Sheet.Root>

	<!-- Delete AlertDialog -->
	<AlertDialog.Root
		open={!!deleteTarget}
		onOpenChange={(o) => {
			if (!o) deleteTarget = null;
		}}
	>
		<AlertDialog.Content>
			<AlertDialog.Header>
				<AlertDialog.Title>Delete Tool</AlertDialog.Title>
				<AlertDialog.Description>
					Delete tool "{deleteTarget?.slug}"? This is permanent and cannot be undone.
				</AlertDialog.Description>
			</AlertDialog.Header>
			<AlertDialog.Footer>
				<AlertDialog.Cancel>Cancel</AlertDialog.Cancel>
				<AlertDialog.Action onclick={confirmDelete}>Delete</AlertDialog.Action>
			</AlertDialog.Footer>
		</AlertDialog.Content>
	</AlertDialog.Root>

	<!-- Table -->
	<div class="rounded-lg border">
		{#if tools.length === 0}
			<p class="py-12 text-center text-sm text-muted-foreground">No tools defined.</p>
		{:else}
			<Table.Root>
				<Table.Header>
					<Table.Row>
						<Table.Head>Slug</Table.Head>
						<Table.Head>Name</Table.Head>
						<Table.Head>Category</Table.Head>
						<Table.Head>Type</Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body>
					{#each tools as t (t.slug)}
						<Table.Row class="cursor-pointer" onclick={() => openEdit(t)}>
							<Table.Cell class="font-mono text-xs">{t.slug}</Table.Cell>
							<Table.Cell class="text-sm font-medium">{t.name}</Table.Cell>
							<Table.Cell class="text-xs text-muted-foreground">{t.category ?? '—'}</Table.Cell>
							<Table.Cell>
								<Badge variant={t.is_builtin ? 'secondary' : 'outline'}>
									{t.is_builtin ? 'Builtin' : 'Custom'}
								</Badge>
							</Table.Cell>
						</Table.Row>
					{/each}
				</Table.Body>
			</Table.Root>
		{/if}
	</div>
</div>
