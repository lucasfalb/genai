<script lang="ts">
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import { superadminApi } from '$lib/api/superadmin';
	import { getErrorMessage } from '$lib/api/client';
	import type { SkillDefinitionResponse } from '$lib/api/types';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import * as Sheet from '$lib/components/ui/sheet/index.js';
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import Cpu from '@lucide/svelte/icons/cpu';
	import Plus from '@lucide/svelte/icons/plus';
	import Trash2 from '@lucide/svelte/icons/trash-2';

	let { data } = $props();

	let skills = $state<SkillDefinitionResponse[]>(data.skills);
	let sheetMode = $state<'create' | 'edit' | null>(null);
	let busy = $state(false);
	let deleteTarget = $state<SkillDefinitionResponse | null>(null);

	// Shared form fields (used for both create and edit)
	let formSlug = $state('');
	let formName = $state('');
	let formDescription = $state('');
	let formCategory = $state('');
	let formPromptBlock = $state('');
	let formExecutor = $state('');
	let formIsActive = $state(true);
	let formRequiresCredential = $state(false);
	let formToolSchema = $state('{}');
	let formInputSchema = $state('{}');
	let formOutputSchema = $state('{}');
	let formCredentialSchema = $state('{}');

	// The skill being edited (edit mode only)
	let editingSkill = $state<SkillDefinitionResponse | null>(null);

	const sheetOpen = $derived(sheetMode !== null);

	function openCreate() {
		formSlug = '';
		formName = '';
		formDescription = '';
		formCategory = '';
		formPromptBlock = '';
		formExecutor = '';
		formIsActive = true;
		formRequiresCredential = false;
		formToolSchema = '{}';
		formInputSchema = '{}';
		formOutputSchema = '{}';
		formCredentialSchema = '{}';
		editingSkill = null;
		sheetMode = 'create';
	}

	function openEdit(s: SkillDefinitionResponse) {
		editingSkill = s;
		formSlug = s.slug;
		formName = s.name;
		formDescription = s.description ?? '';
		formCategory = s.category ?? '';
		formPromptBlock = s.prompt_block ?? '';
		formExecutor = s.executor ?? '';
		formIsActive = s.is_active;
		formRequiresCredential = s.requires_credential ?? false;
		formToolSchema = JSON.stringify(s.tool_schema ?? {}, null, 2);
		formInputSchema = JSON.stringify(s.input_schema ?? {}, null, 2);
		formOutputSchema = JSON.stringify(s.output_schema ?? {}, null, 2);
		formCredentialSchema = JSON.stringify(s.credential_schema ?? {}, null, 2);
		sheetMode = 'edit';
	}

	function parseJSON(raw: string, field: string): Record<string, unknown> | null {
		try {
			return JSON.parse(raw || '{}');
		} catch {
			toast.error(`${field} JSON is invalid.`);
			return null;
		}
	}

	async function save() {
		const toolSchema = parseJSON(formToolSchema, 'Tool schema');
		const inputSchema = parseJSON(formInputSchema, 'Input schema');
		const outputSchema = parseJSON(formOutputSchema, 'Output schema');
		const credentialSchema = parseJSON(formCredentialSchema, 'Credential schema');
		if (!toolSchema || !inputSchema || !outputSchema || !credentialSchema) return;

		if (sheetMode === 'create') {
			if (!formSlug.trim() || !formName.trim()) {
				toast.error('Slug and name are required.');
				return;
			}
			busy = true;
			try {
				const created = await superadminApi.saveSkill(formSlug.trim(), {
					slug: formSlug.trim(),
					name: formName.trim(),
					description: formDescription.trim(),
					category: formCategory.trim(),
					prompt_block: formPromptBlock,
					executor: formExecutor.trim(),
					is_active: formIsActive,
					requires_credential: formRequiresCredential,
					tool_schema: toolSchema,
					input_schema: inputSchema,
					output_schema: outputSchema,
					credential_schema: credentialSchema
				});
				skills = [...skills, created];
				sheetMode = null;
				toast.success('Skill created.');
			} catch (err) {
				toast.error(getErrorMessage(err, 'Create failed.'));
			} finally {
				busy = false;
			}
		} else if (sheetMode === 'edit' && editingSkill) {
			busy = true;
			try {
				const updated = await superadminApi.saveSkill(editingSkill.slug, {
					slug: editingSkill.slug,
					name: formName.trim(),
					description: formDescription.trim(),
					category: formCategory.trim(),
					prompt_block: formPromptBlock,
					executor: formExecutor.trim(),
					is_active: formIsActive,
					requires_credential: formRequiresCredential,
					tool_schema: toolSchema,
					input_schema: inputSchema,
					output_schema: outputSchema,
					credential_schema: credentialSchema
				});
				skills = skills.map((s) => (s.slug === updated.slug ? updated : s));
				editingSkill = updated;
				sheetMode = null;
				toast.success('Skill saved.');
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
			await superadminApi.deleteSkill(target.slug);
			skills = skills.filter((s) => s.slug !== target.slug);
			sheetMode = null;
			toast.success('Skill deleted.');
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
				<Cpu class="size-4" />
			</div>
			<div>
				<h1 class="font-display text-lg font-semibold">Skills</h1>
				<p class="text-xs text-muted-foreground">{skills.length} global skill definitions</p>
			</div>
		</div>
		<Button onclick={openCreate}>
			<Plus data-icon="inline-start" />
			New Skill
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
				<Sheet.Title>{sheetMode === 'create' ? 'New Skill' : `Edit ${editingSkill?.slug}`}</Sheet.Title>
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
						<Input bind:value={formSlug} placeholder="my-skill" class="font-mono" />
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
						<p class="text-sm font-medium">Active</p>
						<Switch bind:checked={formIsActive} />
					</div>
				</div>

				<div class="flex flex-col gap-1.5">
					<label class="text-sm font-medium">Prompt Block</label>
					<Textarea bind:value={formPromptBlock} rows={4} class="font-mono text-xs" />
				</div>

				<div class="grid grid-cols-2 gap-4">
					<div class="flex flex-col gap-1.5">
						<label class="text-sm font-medium">Tool Schema</label>
						<Textarea bind:value={formToolSchema} rows={4} class="font-mono text-xs" />
					</div>
					<div class="flex flex-col gap-1.5">
						<label class="text-sm font-medium">Input Schema</label>
						<Textarea bind:value={formInputSchema} rows={4} class="font-mono text-xs" />
					</div>
					<div class="flex flex-col gap-1.5">
						<label class="text-sm font-medium">Output Schema</label>
						<Textarea bind:value={formOutputSchema} rows={4} class="font-mono text-xs" />
					</div>
					<div class="flex flex-col gap-1.5">
						<label class="text-sm font-medium">Credential Schema</label>
						<Textarea bind:value={formCredentialSchema} rows={4} class="font-mono text-xs" />
					</div>
				</div>
			</div>

			<Sheet.Footer>
				{#if sheetMode === 'edit' && editingSkill}
					<Button
						variant="destructive"
						onclick={() => (deleteTarget = editingSkill)}
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
						{sheetMode === 'create' ? 'Create Skill' : 'Save Skill'}
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
				<AlertDialog.Title>Delete Skill</AlertDialog.Title>
				<AlertDialog.Description>
					Delete skill "{deleteTarget?.slug}"? This is permanent and cannot be undone.
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
		{#if skills.length === 0}
			<p class="py-12 text-center text-sm text-muted-foreground">No skills defined.</p>
		{:else}
			<Table.Root>
				<Table.Header>
					<Table.Row>
						<Table.Head>Slug</Table.Head>
						<Table.Head>Name</Table.Head>
						<Table.Head>Category</Table.Head>
						<Table.Head>Active</Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body>
					{#each skills as s (s.slug)}
						<Table.Row class="cursor-pointer" onclick={() => openEdit(s)}>
							<Table.Cell class="font-mono text-xs">{s.slug}</Table.Cell>
							<Table.Cell class="text-sm font-medium">{s.name}</Table.Cell>
							<Table.Cell class="text-xs text-muted-foreground">{s.category ?? '—'}</Table.Cell>
							<Table.Cell>
								<Badge variant={s.is_active ? 'default' : 'outline'}>
									{s.is_active ? 'Active' : 'Inactive'}
								</Badge>
							</Table.Cell>
						</Table.Row>
					{/each}
				</Table.Body>
			</Table.Root>
		{/if}
	</div>
</div>
