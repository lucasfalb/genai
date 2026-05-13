<script lang="ts">
	import { superadminApi } from '$lib/api/superadmin';
	import { getErrorMessage } from '$lib/api/client';
	import type { ToolDefinitionResponse } from '$lib/api/types';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import RegistryDialog from '$lib/components/registry/RegistryDialog.svelte';
	import Wrench from '@lucide/svelte/icons/wrench';
	import Plus from '@lucide/svelte/icons/plus';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';

	let { data } = $props();

	let tools = $state<ToolDefinitionResponse[]>(data.tools);
	let dialogOpen = $state(false);
	let dialogMode = $state<'create' | 'edit'>('create');
	let editingTool = $state<ToolDefinitionResponse | null>(null);
	let busy = $state(false);

	function openCreate() {
		editingTool = null;
		dialogMode = 'create';
		dialogOpen = true;
	}

	function openEdit(t: ToolDefinitionResponse) {
		editingTool = t;
		dialogMode = 'edit';
		dialogOpen = true;
	}

	async function handleSave(payload: Record<string, unknown>) {
		const slug = (payload.slug as string) || editingTool?.slug || '';
		if (!slug) { toast.error('Slug is required.'); return; }
		busy = true;
		try {
			if (dialogMode === 'create') {
				const created = await superadminApi.saveTool(slug, payload as any);
				tools = [...tools, created];
				toast.success('Tool created.');
			} else {
				const updated = await superadminApi.saveTool(slug, payload as any);
				tools = tools.map((t) => (t.slug === updated.slug ? updated : t));
				toast.success('Tool saved.');
			}
			dialogOpen = false;
		} catch (err) {
			toast.error(getErrorMessage(err, 'Save failed.'));
		} finally {
			busy = false;
		}
	}

	async function handleDelete() {
		if (!editingTool) return;
		busy = true;
		try {
			await superadminApi.deleteTool(editingTool.slug);
			tools = tools.filter((t) => t.slug !== editingTool!.slug);
			dialogOpen = false;
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

	<!-- Registry Dialog -->
	<RegistryDialog
		bind:open={dialogOpen}
		type="tool"
		mode={dialogMode}
		tool={editingTool}
		{busy}
		onSave={handleSave}
		onDelete={handleDelete}
	/>

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
