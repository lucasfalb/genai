<script lang="ts">
	import { superadminApi } from '$lib/api/superadmin';
	import { getErrorMessage } from '$lib/api/client';
	import type { SuperadminUserResponse } from '$lib/api/types';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import * as Sheet from '$lib/components/ui/sheet/index.js';
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import { cn } from '$lib/utils.js';
	import Users from '@lucide/svelte/icons/users';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import Search from '@lucide/svelte/icons/search';

	let { data } = $props();

	const STATUSES = ['active', 'pending', 'suspended'];

	let users = $state<SuperadminUserResponse[]>(data.users);
	let sheetOpen = $state(false);
	let editing = $state<SuperadminUserResponse | null>(null);
	let query = $state('');
	let busy = $state(false);
	let superadminConfirmPending = $state(false);
	let pendingSuperadminValue = $state(false);

	let editName = $state('');
	let editStatus = $state('active');
	let editIsSuperadmin = $state(false);

	const filtered = $derived(
		query.trim()
			? users.filter(
					(u) =>
						u.email.toLowerCase().includes(query.toLowerCase()) ||
						(u.name ?? '').toLowerCase().includes(query.toLowerCase())
				)
			: users
	);

	function statusVariant(status: string): 'default' | 'secondary' | 'destructive' {
		if (status === 'active') return 'default';
		if (status === 'pending') return 'secondary';
		return 'destructive';
	}

	function startEdit(u: SuperadminUserResponse) {
		editing = u;
		editName = u.name ?? '';
		editStatus = u.status;
		editIsSuperadmin = u.is_superadmin;
		sheetOpen = true;
	}

	function handleSuperadminToggle(value: boolean) {
		pendingSuperadminValue = value;
		superadminConfirmPending = true;
	}

	function confirmSuperadminChange() {
		editIsSuperadmin = pendingSuperadminValue;
		superadminConfirmPending = false;
	}

	async function saveEdit() {
		if (!editing) return;
		busy = true;
		try {
			const updated = await superadminApi.updateUser(editing.id, {
				name: editName.trim() || undefined,
				status: editStatus,
				is_superadmin: editIsSuperadmin
			});
			users = users.map((u) => (u.id === updated.id ? updated : u));
			editing = updated;
			toast.success('User updated.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Update failed.'));
		} finally {
			busy = false;
		}
	}

	function initials(u: SuperadminUserResponse): string {
		const src = u.name || u.email;
		return src
			.split(/[\s@.]+/)
			.filter(Boolean)
			.slice(0, 2)
			.map((p) => p[0]?.toUpperCase())
			.join('');
	}
</script>

<div class="flex flex-col gap-6 p-6">
	<div class="flex items-center justify-between gap-4">
		<div class="flex items-center gap-3">
			<div class="flex size-9 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
				<Users class="size-4" />
			</div>
			<div>
				<h1 class="font-display text-lg font-semibold">Users</h1>
				<p class="text-xs text-muted-foreground">{users.length} users</p>
			</div>
		</div>
		<div class="relative">
			<Search class="absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
			<Input
				bind:value={query}
				placeholder="Search users..."
				class="w-55 pl-8"
			/>
		</div>
	</div>

	<!-- Edit Sheet -->
	<Sheet.Root bind:open={sheetOpen}>
		<Sheet.Content side="right" class="w-120 sm:max-w-none overflow-y-auto">
			<Sheet.Header>
				<Sheet.Title>Edit User</Sheet.Title>
				{#if editing}
					<p class="text-xs text-muted-foreground">ID: {editing.id}</p>
				{/if}
			</Sheet.Header>
			{#if editing}
				<div class="flex flex-col gap-4 py-4">
					<div class="flex flex-col gap-1.5">
						<label class="text-sm font-medium">Name</label>
						<Input bind:value={editName} placeholder={editing.email} />
					</div>
					<div class="flex flex-col gap-1.5">
						<label class="text-sm font-medium">Status</label>
						<select bind:value={editStatus} class="h-10 rounded-md border bg-background px-3 text-sm outline-none" style="border-color:var(--ds-border)">
							{#each STATUSES as s (s)}<option value={s}>{s}</option>{/each}
						</select>
					</div>
					<div
						class={cn(
							'flex items-center justify-between rounded-lg border px-3.5 py-3',
							editIsSuperadmin && 'border-amber-500/30 bg-amber-500/5'
						)}
					>
						<div>
							<p class="text-sm font-medium">Superadmin</p>
							<p class="text-xs text-muted-foreground">Full platform access — use with caution.</p>
						</div>
						<Switch
							checked={editIsSuperadmin}
							onCheckedChange={handleSuperadminToggle}
						/>
					</div>
				</div>
			{/if}
			<Sheet.Footer>
				<Button variant="ghost" onclick={() => (sheetOpen = false)}>Cancel</Button>
				<Button disabled={busy} onclick={saveEdit}>
					{#if busy}<Spinner data-icon="inline-start" />{/if}
					{busy ? 'Saving...' : 'Save Changes'}
				</Button>
			</Sheet.Footer>
		</Sheet.Content>
	</Sheet.Root>

	<!-- Superadmin Confirmation AlertDialog -->
	<AlertDialog.Root
		open={superadminConfirmPending}
		onOpenChange={(o) => {
			if (!o) superadminConfirmPending = false;
		}}
	>
		<AlertDialog.Content>
			<AlertDialog.Header>
				<AlertDialog.Title>
					{pendingSuperadminValue ? 'Grant Superadmin?' : 'Revoke Superadmin?'}
				</AlertDialog.Title>
				<AlertDialog.Description>
					{#if pendingSuperadminValue}
						This gives {editing?.email} full platform access. This is a dangerous action.
					{:else}
						This will revoke superadmin privileges from {editing?.email}.
					{/if}
				</AlertDialog.Description>
			</AlertDialog.Header>
			<AlertDialog.Footer>
				<AlertDialog.Cancel onclick={() => (superadminConfirmPending = false)}>Cancel</AlertDialog.Cancel>
				<AlertDialog.Action onclick={confirmSuperadminChange}>Confirm</AlertDialog.Action>
			</AlertDialog.Footer>
		</AlertDialog.Content>
	</AlertDialog.Root>

	<!-- Table -->
	<div class="rounded-lg border">
		{#if filtered.length === 0}
			<p class="py-12 text-center text-sm text-muted-foreground">No users found.</p>
		{:else}
			<Table.Root>
				<Table.Header>
					<Table.Row>
						<Table.Head>User</Table.Head>
						<Table.Head>Status</Table.Head>
						<Table.Head>Role</Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body>
					{#each filtered as u (u.id)}
						<Table.Row
							class="cursor-pointer"
							onclick={() => startEdit(u)}
						>
							<Table.Cell>
								<div class="flex items-center gap-3">
									<div
										class="flex size-8 shrink-0 items-center justify-center rounded-lg bg-muted text-[10px] font-bold ring-1 ring-border"
									>
										{initials(u)}
									</div>
									<div class="min-w-0">
										<p class="truncate text-sm font-medium">{u.name || u.email}</p>
										<p class="truncate text-xs text-muted-foreground">{u.email}</p>
									</div>
								</div>
							</Table.Cell>
							<Table.Cell>
								<Badge variant={statusVariant(u.status)}>{u.status}</Badge>
							</Table.Cell>
							<Table.Cell>
								{#if u.is_superadmin}
									<Badge variant="secondary" class="gap-1">
										<ShieldAlert class="size-3" />
										Superadmin
									</Badge>
								{:else}
									<span class="text-xs text-muted-foreground">User</span>
								{/if}
							</Table.Cell>
						</Table.Row>
					{/each}
				</Table.Body>
			</Table.Root>
		{/if}
	</div>
</div>
