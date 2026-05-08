<script lang="ts">
	import { superadminApi } from '$lib/api/superadmin';
	import { getErrorMessage } from '$lib/api/client';
	import type { SuperadminUserResponse, TenantMemberResponse } from '$lib/api/types';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import * as Command from '$lib/components/ui/command/index.js';
	import UserPlus from '@lucide/svelte/icons/user-plus';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Check from '@lucide/svelte/icons/check';
	import ChevronsUpDown from '@lucide/svelte/icons/chevrons-up-down';

	let { data } = $props();

	const ROLES = [
		{ value: 'tenant_admin', label: 'Admin' },
		{ value: 'member', label: 'Member' },
		{ value: 'viewer', label: 'Viewer' }
	];
	const STATUSES = [
		{ value: 'active', label: 'Active' },
		{ value: 'pending', label: 'Pending' },
		{ value: 'suspended', label: 'Suspended' }
	];

	let members = $state<TenantMemberResponse[]>(data.members);
	let users = $state<SuperadminUserResponse[]>(data.users);
	let busy = $state(false);
	let removingTarget = $state<TenantMemberResponse | null>(null);
	let addOpen = $state(false);
	let userComboboxOpen = $state(false);
	let selectedUserId = $state('');
	let addRole = $state('member');

	function getRoleLabel(value: string) {
		return ROLES.find((r) => r.value === value)?.label ?? value;
	}

	function getStatusLabel(value: string) {
		return STATUSES.find((s) => s.value === value)?.label ?? value;
	}

	const availableUsers = $derived(
		users.filter(
			(user) =>
				user.status === 'active' &&
				!members.some((member) => member.user_id === user.id)
		)
	);
	const selectedUser = $derived(users.find((user) => user.id === selectedUserId) ?? null);

	function resetAddDialog() {
		selectedUserId = '';
		addRole = 'member';
		userComboboxOpen = false;
	}

	async function addMember() {
		if (!selectedUser) {
			toast.error('Select a user.');
			return;
		}
		const role = String(addRole);
		busy = true;
		try {
			const m = await superadminApi.addTenantMember(data.tenant.id, {
				email: selectedUser.email,
				role
			});
			members = [...members.filter((x) => x.user_id !== m.user_id), m];
			resetAddDialog();
			addOpen = false;
			toast.success('Member added.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Add failed.'));
		} finally {
			busy = false;
		}
	}

	async function changeRole(m: TenantMemberResponse, role: string) {
		try {
			const updated = await superadminApi.updateTenantMember(data.tenant.id, m.user_id, {
				role: String(role)
			});
			members = members.map((x) => (x.user_id === updated.user_id ? updated : x));
		} catch (err) {
			toast.error(getErrorMessage(err, 'Update failed.'));
		}
	}

	async function changeStatus(m: TenantMemberResponse, status: string) {
		try {
			const updated = await superadminApi.updateTenantMember(data.tenant.id, m.user_id, {
				status: String(status)
			});
			members = members.map((x) => (x.user_id === updated.user_id ? updated : x));
		} catch (err) {
			toast.error(getErrorMessage(err, 'Update failed.'));
		}
	}

	async function confirmRemove() {
		if (!removingTarget) return;
		const target = removingTarget;
		removingTarget = null;
		try {
			await superadminApi.removeTenantMember(data.tenant.id, target.user_id);
			members = members.filter((x) => x.user_id !== target.user_id);
			toast.success('Member removed.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Remove failed.'));
		}
	}
</script>

<div class="flex flex-col gap-4 p-6">
	<div class="flex items-center justify-between">
		<div class="flex items-center gap-2">
			<span class="text-sm font-semibold">Members</span>
			<Badge variant="secondary">{members.length}</Badge>
		</div>
		<Button onclick={() => (addOpen = true)}>
			<UserPlus data-icon="inline-start" />
			Add Member
		</Button>
	</div>

	<!-- Add Member Dialog -->
	<Dialog.Root
		bind:open={addOpen}
		onOpenChange={(open) => {
			if (!open) resetAddDialog();
		}}
	>
		<Dialog.Content class="sm:max-w-md">
			<Dialog.Header>
				<Dialog.Title>Add Member</Dialog.Title>
				<Dialog.Description>Select an existing active user and assign a tenant role.</Dialog.Description>
			</Dialog.Header>
			<div class="flex flex-col gap-4">
				<div class="flex flex-col gap-1.5">
					<label class="text-sm font-medium">User</label>
					<Popover.Root bind:open={userComboboxOpen}>
						<Popover.Trigger>
							{#snippet child({ props })}
								<Button
									{...props}
									variant="outline"
									class="w-full justify-between"
									role="combobox"
									aria-expanded={userComboboxOpen}
								>
									<span class="truncate">
										{selectedUser ? `${selectedUser.name || selectedUser.email} - ${selectedUser.email}` : 'Select user...'}
									</span>
									<ChevronsUpDown class="opacity-50" />
								</Button>
							{/snippet}
						</Popover.Trigger>
						<Popover.Content class="w-[360px] p-0">
							<Command.Root>
								<Command.Input placeholder="Search user..." />
								<Command.List>
									<Command.Empty>No available users.</Command.Empty>
									<Command.Group>
										{#each availableUsers as user (user.id)}
											<Command.Item
												value={`${user.email} ${user.name ?? ''}`}
												onSelect={() => {
													selectedUserId = user.id;
													userComboboxOpen = false;
												}}
											>
												<Check class={selectedUserId === user.id ? 'size-4' : 'size-4 text-transparent'} />
												<div class="min-w-0">
													<p class="truncate text-sm font-medium">{user.name || user.email}</p>
													<p class="truncate text-xs text-muted-foreground">{user.email}</p>
												</div>
											</Command.Item>
										{/each}
									</Command.Group>
								</Command.List>
							</Command.Root>
						</Popover.Content>
					</Popover.Root>
				</div>
				<div class="flex flex-col gap-1.5">
					<label class="text-sm font-medium">Role</label>
					<select
						bind:value={addRole}
						class="h-10 rounded-md border bg-background px-3 text-sm outline-none"
						style="border-color:var(--ds-border)"
					>
						{#each ROLES as r (r.value)}
							<option value={r.value}>{r.label}</option>
						{/each}
					</select>
				</div>
			</div>
			<Dialog.Footer>
				<Button variant="ghost" onclick={() => (addOpen = false)}>Cancel</Button>
				<Button disabled={busy || !selectedUser} onclick={addMember}>
					{#if busy}<Spinner data-icon="inline-start" />{/if}
					{busy ? 'Adding...' : 'Add Member'}
				</Button>
			</Dialog.Footer>
		</Dialog.Content>
	</Dialog.Root>

	<!-- Remove Confirmation AlertDialog -->
	<AlertDialog.Root
		open={!!removingTarget}
		onOpenChange={(o) => {
			if (!o) removingTarget = null;
		}}
	>
		<AlertDialog.Content>
			<AlertDialog.Header>
				<AlertDialog.Title>Remove Member</AlertDialog.Title>
				<AlertDialog.Description>
					Remove {removingTarget?.email} from this tenant? This action cannot be undone.
				</AlertDialog.Description>
			</AlertDialog.Header>
			<AlertDialog.Footer>
				<AlertDialog.Cancel>Cancel</AlertDialog.Cancel>
				<AlertDialog.Action onclick={confirmRemove}>Remove</AlertDialog.Action>
			</AlertDialog.Footer>
		</AlertDialog.Content>
	</AlertDialog.Root>

	<!-- Table -->
	<div class="overflow-hidden rounded-lg border" style="border-color:var(--ds-border);background:var(--surface)">
		{#if members.length === 0}
			<p class="py-12 text-center text-sm text-muted-foreground">No members.</p>
		{:else}
			<Table.Root>
				<Table.Header>
					<Table.Row>
						<Table.Head>User</Table.Head>
						<Table.Head>Role</Table.Head>
						<Table.Head>Status</Table.Head>
						<Table.Head></Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body>
					{#each members as m (m.user_id)}
						<Table.Row>
							<Table.Cell>
								<p class="text-sm font-medium">{m.name || m.email}</p>
								<p class="text-xs text-muted-foreground">{m.email}</p>
							</Table.Cell>
							<Table.Cell>
								<select
									value={m.role}
									onchange={(event) => changeRole(m, event.currentTarget.value)}
									class="h-9 w-36 rounded-md border bg-background px-2 text-sm outline-none"
									style="border-color:var(--ds-border)"
									aria-label="Member role"
								>
									{#each ROLES as r (r.value)}
										<option value={r.value}>{getRoleLabel(r.value)}</option>
									{/each}
								</select>
							</Table.Cell>
							<Table.Cell>
								<select
									value={m.status}
									onchange={(event) => changeStatus(m, event.currentTarget.value)}
									class="h-9 w-36 rounded-md border bg-background px-2 text-sm outline-none"
									style="border-color:var(--ds-border)"
									aria-label="Member status"
								>
									{#each STATUSES as s (s.value)}
										<option value={s.value}>{getStatusLabel(s.value)}</option>
									{/each}
								</select>
							</Table.Cell>
							<Table.Cell class="text-right">
								<Button
									variant="destructive"
									size="icon-sm"
									onclick={() => (removingTarget = m)}
								>
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
