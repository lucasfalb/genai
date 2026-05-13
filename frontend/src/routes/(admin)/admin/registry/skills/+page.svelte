<script lang="ts">
	import { superadminApi } from '$lib/api/superadmin';
	import { getErrorMessage } from '$lib/api/client';
	import type { SkillDefinitionResponse } from '$lib/api/types';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import RegistryDialog from '$lib/components/registry/RegistryDialog.svelte';
	import Cpu from '@lucide/svelte/icons/cpu';
	import Plus from '@lucide/svelte/icons/plus';

	let { data } = $props();

	let skills = $state<SkillDefinitionResponse[]>(data.skills);
	let dialogOpen = $state(false);
	let dialogMode = $state<'create' | 'edit'>('create');
	let editingSkill = $state<SkillDefinitionResponse | null>(null);
	let busy = $state(false);

	function openCreate() {
		editingSkill = null;
		dialogMode = 'create';
		dialogOpen = true;
	}

	function openEdit(s: SkillDefinitionResponse) {
		editingSkill = s;
		dialogMode = 'edit';
		dialogOpen = true;
	}

	async function handleSave(payload: Record<string, unknown>) {
		const slug = (payload.slug as string) || editingSkill?.slug || '';
		if (!slug) { toast.error('Slug is required.'); return; }
		busy = true;
		try {
			if (dialogMode === 'create') {
				const created = await superadminApi.saveSkill(slug, payload as any);
				skills = [...skills, created];
				toast.success('Skill created.');
			} else {
				const updated = await superadminApi.saveSkill(slug, payload as any);
				skills = skills.map((s) => (s.slug === updated.slug ? updated : s));
				toast.success('Skill saved.');
			}
			dialogOpen = false;
		} catch (err) {
			toast.error(getErrorMessage(err, 'Save failed.'));
		} finally {
			busy = false;
		}
	}

	async function handleDelete() {
		if (!editingSkill) return;
		busy = true;
		try {
			await superadminApi.deleteSkill(editingSkill.slug);
			skills = skills.filter((s) => s.slug !== editingSkill!.slug);
			dialogOpen = false;
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

	<!-- Registry Dialog -->
	<RegistryDialog
		bind:open={dialogOpen}
		type="skill"
		mode={dialogMode}
		skill={editingSkill}
		{busy}
		onSave={handleSave}
		onDelete={handleDelete}
	/>

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
