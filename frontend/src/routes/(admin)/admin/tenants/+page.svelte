<script lang="ts">
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { superadminApi } from '$lib/api/superadmin';
	import { getErrorMessage } from '$lib/api/client';
	import type { SuperadminTenantResponse } from '$lib/api/types';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import Building2 from '@lucide/svelte/icons/building-2';
	import Plus from '@lucide/svelte/icons/plus';
	import Pencil from '@lucide/svelte/icons/pencil';
	import ArrowRight from '@lucide/svelte/icons/arrow-right';

	let { data } = $props();

	const PLANS = ['free', 'pro', 'enterprise'];
	const STATUSES = ['active', 'pending', 'suspended'];

	let tenants = $state<SuperadminTenantResponse[]>(data.tenants);
	let editDialogOpen = $state(false);
	let createDialogOpen = $state(false);
	let editing = $state<SuperadminTenantResponse | null>(null);
	let busy = $state(false);

	// Edit form
	let editName = $state('');
	let editPlan = $state('free');
	let editStatus = $state('active');
	let editSettings = $state('{}');

	// Create form
	let newSlug = $state('');
	let newName = $state('');
	let newPlan = $state('free');
	let newStatus = $state('active');

	function planVariant(plan: string): 'default' | 'secondary' | 'outline' {
		if (plan === 'enterprise') return 'default';
		if (plan === 'pro') return 'secondary';
		return 'outline';
	}

	function startEdit(t: SuperadminTenantResponse) {
		editing = t;
		editName = t.name;
		editPlan = t.plan;
		editStatus = t.status;
		editSettings = JSON.stringify(t.settings ?? {}, null, 2);
		editDialogOpen = true;
	}

	function openCreate() {
		newSlug = '';
		newName = '';
		newPlan = 'free';
		newStatus = 'active';
		createDialogOpen = true;
	}

	async function saveEdit() {
		if (!editing) return;
		let parsedSettings: Record<string, unknown> = {};
		try {
			parsedSettings = JSON.parse(editSettings || '{}');
		} catch {
			toast.error('Settings JSON is invalid.');
			return;
		}
		busy = true;
		try {
			const updated = await superadminApi.updateTenant(editing.id, {
				name: editName.trim(),
				plan: editPlan,
				status: editStatus,
				settings: parsedSettings
			});
			tenants = tenants.map((t) => (t.id === updated.id ? updated : t));
			editing = updated;
			editDialogOpen = false;
			toast.success('Tenant updated.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Update failed.'));
		} finally {
			busy = false;
		}
	}

	async function createTenant() {
		if (!newSlug.trim() || !newName.trim()) {
			toast.error('Slug and name are required.');
			return;
		}
		busy = true;
		try {
			const created = await superadminApi.createTenant({
				slug: newSlug.trim(),
				name: newName.trim(),
				plan: newPlan,
				status: newStatus
			});
			tenants = [...tenants, created];
			createDialogOpen = false;
			toast.success('Tenant created.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Create failed.'));
		} finally {
			busy = false;
		}
	}
</script>

<div class="flex flex-col gap-6 p-6">
	<div class="flex items-center justify-between gap-4">
		<div class="flex items-center gap-3">
			<div class="flex size-9 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
				<Building2 class="size-4" />
			</div>
			<div>
				<h1 class="font-display text-lg font-semibold">Tenants</h1>
				<p class="text-xs text-muted-foreground">{tenants.length} tenants</p>
			</div>
		</div>
		<Button onclick={openCreate}>
			<Plus data-icon="inline-start" />
			New Tenant
		</Button>
	</div>

	<!-- Create Dialog -->
	<Dialog.Root bind:open={createDialogOpen}>
		<Dialog.Content class="sm:max-w-md">
			<Dialog.Header>
				<Dialog.Title>Create Tenant</Dialog.Title>
				<Dialog.Description>Add a new tenant to the platform.</Dialog.Description>
			</Dialog.Header>
			<div class="grid grid-cols-2 gap-4">
				<div class="flex flex-col gap-1.5">
					<label class="text-sm font-medium">Slug</label>
					<Input bind:value={newSlug} placeholder="acme-corp" class="font-mono" />
				</div>
				<div class="flex flex-col gap-1.5">
					<label class="text-sm font-medium">Name</label>
					<Input bind:value={newName} placeholder="Acme Corp" />
				</div>
				<div class="flex flex-col gap-1.5">
					<label class="text-sm font-medium">Plan</label>
					<select bind:value={newPlan} class="h-10 rounded-md border bg-background px-3 text-sm outline-none" style="border-color:var(--ds-border)">
						{#each PLANS as p (p)}<option value={p}>{p}</option>{/each}
					</select>
				</div>
				<div class="flex flex-col gap-1.5">
					<label class="text-sm font-medium">Status</label>
					<select bind:value={newStatus} class="h-10 rounded-md border bg-background px-3 text-sm outline-none" style="border-color:var(--ds-border)">
						{#each STATUSES as s (s)}<option value={s}>{s}</option>{/each}
					</select>
				</div>
			</div>
			<Dialog.Footer>
				<Button variant="ghost" onclick={() => (createDialogOpen = false)}>Cancel</Button>
				<Button disabled={busy} onclick={createTenant}>
					{#if busy}<Spinner data-icon="inline-start" />{/if}
					{busy ? 'Creating...' : 'Create Tenant'}
				</Button>
			</Dialog.Footer>
		</Dialog.Content>
	</Dialog.Root>

	<!-- Edit Dialog -->
	<Dialog.Root bind:open={editDialogOpen}>
		<Dialog.Content class="sm:max-w-lg">
			<Dialog.Header>
				<Dialog.Title>Edit {editing?.slug}</Dialog.Title>
				<Dialog.Description>Slug is immutable after creation.</Dialog.Description>
			</Dialog.Header>
			<div class="flex flex-col gap-4">
				<div class="grid grid-cols-3 gap-4">
					<div class="col-span-3 flex flex-col gap-1.5 sm:col-span-1">
						<label class="text-sm font-medium">Name</label>
						<Input bind:value={editName} />
					</div>
					<div class="flex flex-col gap-1.5">
						<label class="text-sm font-medium">Plan</label>
						<select bind:value={editPlan} class="h-10 rounded-md border bg-background px-3 text-sm outline-none" style="border-color:var(--ds-border)">
							{#each PLANS as p (p)}<option value={p}>{p}</option>{/each}
						</select>
					</div>
					<div class="flex flex-col gap-1.5">
						<label class="text-sm font-medium">Status</label>
						<select bind:value={editStatus} class="h-10 rounded-md border bg-background px-3 text-sm outline-none" style="border-color:var(--ds-border)">
							{#each STATUSES as s (s)}<option value={s}>{s}</option>{/each}
						</select>
					</div>
				</div>
				<div class="flex flex-col gap-1.5">
					<label class="text-sm font-medium">Settings JSON</label>
					<Textarea bind:value={editSettings} rows={4} class="font-mono text-xs" />
				</div>
			</div>
			<Dialog.Footer>
				<Button variant="ghost" onclick={() => (editDialogOpen = false)}>Cancel</Button>
				<Button disabled={busy} onclick={saveEdit}>
					{#if busy}<Spinner data-icon="inline-start" />{/if}
					{busy ? 'Saving...' : 'Save Changes'}
				</Button>
			</Dialog.Footer>
		</Dialog.Content>
	</Dialog.Root>

	<!-- Table -->
	<div class="overflow-hidden rounded-lg border" style="border-color:var(--ds-border);background:var(--surface)">
		{#if tenants.length === 0}
			<p class="py-12 text-center text-sm text-muted-foreground">No tenants found.</p>
		{:else}
			<Table.Root>
				<Table.Header>
					<Table.Row>
						<Table.Head>Slug</Table.Head>
						<Table.Head>Name</Table.Head>
						<Table.Head>Plan</Table.Head>
						<Table.Head>Status</Table.Head>
						<Table.Head></Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body>
					{#each tenants as t (t.id)}
						<Table.Row>
							<Table.Cell class="font-mono text-xs">{t.slug}</Table.Cell>
							<Table.Cell class="text-sm font-medium">{t.name}</Table.Cell>
							<Table.Cell>
								<Badge variant={planVariant(t.plan)}>{t.plan}</Badge>
							</Table.Cell>
							<Table.Cell>
								<StatusBadge status={t.status} />
							</Table.Cell>
							<Table.Cell>
								<div class="flex items-center justify-end gap-2">
									<Button
										variant="ghost"
										size="icon-sm"
										onclick={() => startEdit(t)}
										title="Edit"
									>
										<Pencil />
									</Button>
									<a
										href="/admin/tenants/{t.id}"
										class="inline-flex h-8 items-center gap-1.5 rounded-md border px-3 text-xs font-medium transition-colors hover:bg-accent hover:text-accent-foreground"
										style="border-color:var(--ds-border)"
										title="Open tenant details"
									>
										Open
										<ArrowRight class="size-3.5" />
									</a>
								</div>
							</Table.Cell>
						</Table.Row>
					{/each}
				</Table.Body>
			</Table.Root>
		{/if}
	</div>
</div>
