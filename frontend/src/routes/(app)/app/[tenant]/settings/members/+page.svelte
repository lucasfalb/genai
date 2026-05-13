<script lang="ts">
	import RoleBadge from '$lib/components/RoleBadge.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { membersApi } from '$lib/api/members';
	import { invitationsApi } from '$lib/api/invitations';
	import { ApiError, getErrorMessage } from '$lib/api/client';
	import type { TenantInvitationResponse, TenantMemberResponse } from '$lib/api/types';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import X from '@lucide/svelte/icons/x';
	import Search from '@lucide/svelte/icons/search';
	import UserPlus from '@lucide/svelte/icons/user-plus';
	import { toast } from 'svelte-sonner';

	import * as Table from '$lib/components/ui/table';
	import * as Tabs from '$lib/components/ui/tabs';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as AlertDialog from '$lib/components/ui/alert-dialog';
	import * as Select from '$lib/components/ui/select';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';

	let { data } = $props();

	let members = $state<TenantMemberResponse[]>(data.members);
	let invitations = $state<TenantInvitationResponse[]>(data.invitations);
	let busyUserId = $state('');
	let email = $state('');
	let inviteRole = $state('member');
	let creating = $state(false);
	let busyInvitationId = $state('');
	let inviteOpen = $state(false);

	// Removal/Cancel state
	let memberToRemove = $state<TenantMemberResponse | null>(null);
	let invitationToCancel = $state<TenantInvitationResponse | null>(null);

	// Search state
	let searchQuery = $state('');

	const ASSIGNABLE_ROLES = [
		{ value: 'tenant_admin', label: 'Tenant Admin' },
		{ value: 'member', label: 'Member' },
		{ value: 'viewer', label: 'Viewer' }
	];

	const ASSIGNABLE_STATUS = [
		{ value: 'active', label: 'Active' },
		{ value: 'pending', label: 'Pending' },
		{ value: 'suspended', label: 'Suspended' }
	];

	const filteredMembers = $derived(
		members.filter((m) => {
			const name = (m.name || '').toLowerCase();
			const mEmail = (m.email || '').toLowerCase();
			const query = searchQuery.toLowerCase();
			return name.includes(query) || mEmail.includes(query);
		})
	);

	const filteredInvitations = $derived(
		invitations.filter((i) => {
			const iEmail = (i.email || '').toLowerCase();
			const query = searchQuery.toLowerCase();
			return iEmail.includes(query);
		})
	);

	function initials(member: TenantMemberResponse): string {
		const source = member.name || member.email || '?';
		return source
			.split(/[\s@.]+/)
			.filter(Boolean)
			.slice(0, 2)
			.map((part) => part[0]?.toUpperCase())
			.join('');
	}

	function canEdit(member: TenantMemberResponse): boolean {
		return (
			member.user_id !== data.currentUserId &&
			member.role !== 'owner' &&
			member.role !== 'superadmin'
		);
	}

	async function updateMember(
		member: TenantMemberResponse,
		patch: { role?: string; status?: string }
	) {
		if (!canEdit(member)) return;
		busyUserId = member.user_id;
		try {
			const updated = await membersApi.update(member.user_id, patch);
			members = members.map((item) => (item.user_id === updated.user_id ? updated : item));
			toast.success('Member updated.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Member update failed.'));
		} finally {
			busyUserId = '';
		}
	}

	async function removeMember() {
		if (!memberToRemove) return;
		const target = memberToRemove;
		memberToRemove = null;
		busyUserId = target.user_id;
		try {
			await membersApi.remove(target.user_id);
			members = members.filter((item) => item.user_id !== target.user_id);
			toast.success('Member removed.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Member removal failed.'));
		} finally {
			busyUserId = '';
		}
	}

	function formatExpiry(value: string): string {
		const date = new Date(value);
		if (Number.isNaN(date.getTime())) return value;
		const ms = date.getTime() - Date.now();
		const days = Math.ceil(ms / (1000 * 60 * 60 * 24));
		if (days > 1) return `Expires in ${days} days`;
		if (days === 1) return 'Expires tomorrow';
		if (days === 0 && ms > 0) return 'Expires today';
		return `Expired on ${date.toLocaleDateString()}`;
	}

	function effectiveStatus(invitation: TenantInvitationResponse): string {
		if (
			invitation.status === 'pending' &&
			new Date(invitation.expires_at).getTime() <= Date.now()
		) {
			return 'expired';
		}
		return invitation.status;
	}

	async function createInvitation() {
		if (!email.trim()) {
			toast.error('Email is required.');
			return;
		}
		creating = true;
		try {
			const created = await invitationsApi.create({ email: email.trim(), role: inviteRole });
			invitations = [created, ...invitations.filter((item) => item.id !== created.id)];
			email = '';
			inviteRole = 'member';
			inviteOpen = false;
			toast.success('Invitation created.');
		} catch (err) {
			if (err instanceof ApiError && err.status === 409) {
				toast.error('Email already invited or already a tenant member.');
			} else {
				toast.error(getErrorMessage(err, 'Invitation failed.'));
			}
		} finally {
			creating = false;
		}
	}

	async function resendInvitation(invitation: TenantInvitationResponse) {
		busyInvitationId = invitation.id;
		try {
			const resent = await invitationsApi.resend(invitation.id);
			invitations = invitations.map((item) => (item.id === invitation.id ? resent : item));
			toast.success('Invitation resent.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Invitation resend failed.'));
		} finally {
			busyInvitationId = '';
		}
	}

	async function cancelInvitation() {
		if (!invitationToCancel) return;
		const target = invitationToCancel;
		invitationToCancel = null;
		busyInvitationId = target.id;
		try {
			await invitationsApi.cancel(target.id);
			invitations = invitations.filter((item) => item.id !== target.id);
			toast.success('Invitation cancelled.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Invitation cancel failed.'));
		} finally {
			busyInvitationId = '';
		}
	}
</script>

<div class="flex flex-col gap-3 p-4">
	<Tabs.Root value="members" class="w-full gap-3">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<Tabs.List class="bg-muted p-1">
				<Tabs.Trigger value="members" class="px-6">Members</Tabs.Trigger>
				<Tabs.Trigger value="invitations" class="px-6">
					Invitations
					{#if invitations.length > 0}
						<span class="ml-2 rounded-full bg-blue-500/20 px-1.5 py-0.5 text-[10px] text-blue-400">
							{invitations.length}
						</span>
					{/if}
				</Tabs.Trigger>
			</Tabs.List>

			<div class="flex items-center gap-3">
				<!-- Search -->
				<div class="relative w-full max-w-xs">
					<Search class="absolute top-2.5 left-2.5 h-4 w-4 text-muted-foreground" />
					<Input placeholder="Search..." bind:value={searchQuery} class="h-9 bg-background pl-9" />
				</div>

				<Button onclick={() => (inviteOpen = true)} size="sm" class="h-9 gap-2">
					<UserPlus class="h-4 w-4" />
					Invite Member
				</Button>
			</div>
		</div>

		<Tabs.Content value="members" class="mt-0">
			<div class="overflow-hidden border bg-card">
				<Table.Root containerClass="scrollbar-none bg-card" class="w-full table-fixed">
					<Table.Header class="bg-background">
						<Table.Row class="bg-background hover:bg-background">
							<Table.Head
								class="w-[40%] bg-background py-2 text-[11px] font-bold tracking-wider uppercase"
								>User</Table.Head
							>
							<Table.Head class="bg-background py-2 text-[11px] font-bold tracking-wider uppercase"
								>Role</Table.Head
							>
							<Table.Head
								class="w-[120px] bg-background py-2 text-[11px] font-bold tracking-wider uppercase"
								>Status</Table.Head
							>
							<Table.Head class="w-[100px] bg-background py-2"></Table.Head>
						</Table.Row>
					</Table.Header>

					<Table.Body>
						{#if filteredMembers.length === 0}
							<Table.Row class="bg-card hover:bg-card">
								<Table.Cell colspan={4} class="h-32 text-center text-muted-foreground">
									<div class="flex flex-col items-center gap-1">
										<span class="text-sm font-medium text-foreground">No members found</span>
										<span class="text-xs">Try adjusting your search query.</span>
									</div>
								</Table.Cell>
							</Table.Row>
						{:else}
							{#each filteredMembers as member (member.user_id)}
								{@const isSelf = member.user_id === data.currentUserId}
								{@const editable = canEdit(member)}
								{@const busy = busyUserId === member.user_id}
								<Table.Row class="group bg-card transition-colors hover:bg-muted/30">
									<Table.Cell class="py-3">
										<div class="flex items-center gap-3 overflow-hidden">
											<div
												class="flex h-9 w-9 shrink-0 items-center justify-center border bg-background text-[10px] font-bold text-muted-foreground uppercase transition-all group-hover:border-primary/40"
											>
												{initials(member)}
											</div>
											<div class="min-w-0">
												<p class="truncate text-sm font-semibold">
													{member.name || member.email}
													{#if isSelf}<span
															class="ml-1 text-[10px] font-normal tracking-tighter text-muted-foreground uppercase"
															>(you)</span
														>{/if}
												</p>
												<p class="truncate text-[10px] text-muted-foreground">{member.email}</p>
											</div>
										</div>
									</Table.Cell>

									<Table.Cell class="py-3">
										{#if editable}
											<Select.Root
												type="single"
												value={member.role}
												onValueChange={(v) => updateMember(member, { role: v })}
												disabled={busy}
											>
												<Select.Trigger class="h-8 w-full max-w-[140px] bg-background text-xs">
													{ASSIGNABLE_ROLES.find((r) => r.value === member.role)?.label ||
														member.role}
												</Select.Trigger>
												<Select.Content>
													{#each ASSIGNABLE_ROLES as role}
														<Select.Item value={role.value}>{role.label}</Select.Item>
													{/each}
												</Select.Content>
											</Select.Root>
										{:else}
											<RoleBadge role={member.role} />
										{/if}
									</Table.Cell>

									<Table.Cell class="py-3">
										{#if editable}
											<Select.Root
												type="single"
												value={member.status}
												onValueChange={(v) => updateMember(member, { status: v })}
												disabled={busy}
											>
												<Select.Trigger class="h-8 w-full max-w-[110px] bg-background text-xs">
													{ASSIGNABLE_STATUS.find((s) => s.value === member.status)?.label ||
														member.status}
												</Select.Trigger>
												<Select.Content>
													{#each ASSIGNABLE_STATUS as status}
														<Select.Item value={status.value}>{status.label}</Select.Item>
													{/each}
												</Select.Content>
											</Select.Root>
										{:else}
											<StatusBadge status={member.status} />
										{/if}
									</Table.Cell>

									<Table.Cell class="py-3 text-right">
										{#if editable}
											<Button
												variant="ghost"
												size="sm"
												onclick={() => (memberToRemove = member)}
												disabled={busy}
												class="h-8 gap-1.5 text-xs text-red-400 hover:bg-red-400/10 hover:text-red-400"
											>
												<Trash2 class="h-3.5 w-3.5" />
												Remove
											</Button>
										{/if}
									</Table.Cell>
								</Table.Row>
							{/each}
						{/if}
					</Table.Body>
				</Table.Root>
				<div class="border-t bg-card px-4 py-2">
					<p class="text-[10px] font-bold tracking-widest text-muted-foreground uppercase">
						Showing {filteredMembers.length} of {members.length} members
					</p>
				</div>
			</div>
		</Tabs.Content>

		<Tabs.Content value="invitations" class="mt-0">
			<div class="overflow-hidden border bg-card">
				<Table.Root containerClass="scrollbar-none bg-card" class="w-full table-fixed">
					<Table.Header class="bg-background">
						<Table.Row class="bg-background hover:bg-background">
							<Table.Head
								class="w-[40%] bg-background py-2 text-[11px] font-bold tracking-wider uppercase"
								>Email</Table.Head
							>
							<Table.Head class="bg-background py-2 text-[11px] font-bold tracking-wider uppercase"
								>Role</Table.Head
							>
							<Table.Head class="bg-background py-2 text-[11px] font-bold tracking-wider uppercase"
								>Status</Table.Head
							>
							<Table.Head
								class="w-[120px] bg-background py-2 text-right text-[11px] font-bold tracking-wider uppercase"
								>Actions</Table.Head
							>
						</Table.Row>
					</Table.Header>

					<Table.Body>
						{#if filteredInvitations.length === 0}
							<Table.Row class="bg-card hover:bg-card">
								<Table.Cell colspan={4} class="h-32 text-center text-muted-foreground">
									<div class="flex flex-col items-center gap-1">
										<span class="text-sm font-medium text-foreground">No invitations found</span>
										<span class="text-xs">
											{searchQuery
												? 'Try adjusting your search query.'
												: 'Invite someone to get started.'}
										</span>
									</div>
								</Table.Cell>
							</Table.Row>
						{:else}
							{#each filteredInvitations as invitation (invitation.id)}
								{@const status = effectiveStatus(invitation)}
								{@const busy = busyInvitationId === invitation.id}
								<Table.Row class="group bg-card transition-colors hover:bg-muted/30">
									<Table.Cell class="py-3">
										<div class="min-w-0">
											<p class="truncate text-sm font-semibold">{invitation.email}</p>
											<p
												class="truncate text-[10px] tracking-tighter text-muted-foreground uppercase"
											>
												{formatExpiry(invitation.expires_at)}
											</p>
										</div>
									</Table.Cell>

									<Table.Cell class="py-3">
										<RoleBadge role={invitation.role} />
									</Table.Cell>

									<Table.Cell class="py-3">
										<StatusBadge {status} />
									</Table.Cell>

									<Table.Cell class="py-3 text-right">
										<div class="flex items-center justify-end gap-1">
											<Button
												variant="ghost"
												size="icon-sm"
												onclick={() => resendInvitation(invitation)}
												disabled={busy || status === 'accepted'}
												class="text-blue-400 hover:bg-blue-400/10 hover:text-blue-400"
											>
												<RefreshCw class="h-3.5 w-3.5" />
											</Button>
											<Button
												variant="ghost"
												size="icon-sm"
												onclick={() => (invitationToCancel = invitation)}
												disabled={busy || status !== 'pending'}
												class="text-red-400 hover:bg-red-400/10 hover:text-red-400"
											>
												<X class="h-3.5 w-3.5" />
											</Button>
										</div>
									</Table.Cell>
								</Table.Row>
							{/each}
						{/if}
					</Table.Body>
				</Table.Root>
				<div class="border-t bg-card px-4 py-2">
					<p class="text-[10px] font-bold tracking-widest text-muted-foreground uppercase">
						Showing {filteredInvitations.length} of {invitations.length} invitations
					</p>
				</div>
			</div>
		</Tabs.Content>
	</Tabs.Root>
</div>

<!-- Invite Dialog -->
<Dialog.Root bind:open={inviteOpen}>
	<Dialog.Content class="sm:max-w-[425px]">
		<Dialog.Header>
			<Dialog.Title>Invite Member</Dialog.Title>
			<Dialog.Description>
				Send an invitation to join this tenant. They will receive an email with a link to join.
			</Dialog.Description>
		</Dialog.Header>

		<div class="grid gap-4 py-4">
			<div class="grid gap-2">
				<Label for="email">Email address</Label>
				<Input id="email" type="email" bind:value={email} placeholder="name@company.com" />
			</div>
			<div class="grid gap-2">
				<Label for="role">Role</Label>
				<Select.Root type="single" bind:value={inviteRole}>
					<Select.Trigger class="w-full bg-background">
						{ASSIGNABLE_ROLES.find((r) => r.value === inviteRole)?.label}
					</Select.Trigger>
					<Select.Content>
						{#each ASSIGNABLE_ROLES as role}
							<Select.Item value={role.value}>{role.label}</Select.Item>
						{/each}
					</Select.Content>
				</Select.Root>
			</div>
		</div>

		<Dialog.Footer>
			<Button variant="outline" onclick={() => (inviteOpen = false)}>Cancel</Button>
			<Button onclick={createInvitation} disabled={creating || !email.trim()}>
				{creating ? 'Sending...' : 'Send Invitation'}
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<!-- Remove Member AlertDialog -->
<AlertDialog.Root
	open={!!memberToRemove}
	onOpenChange={(o) => {
		if (!o) memberToRemove = null;
	}}
>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Remove Member</AlertDialog.Title>
			<AlertDialog.Description>
				Are you sure you want to remove <strong class="text-foreground"
					>{memberToRemove?.name || memberToRemove?.email}</strong
				> from this tenant? This user will lose all access immediately.
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>Cancel</AlertDialog.Cancel>
			<Button variant="destructive" onclick={removeMember}>Remove</Button>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>

<!-- Cancel Invitation AlertDialog -->
<AlertDialog.Root
	open={!!invitationToCancel}
	onOpenChange={(o) => {
		if (!o) invitationToCancel = null;
	}}
>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Cancel Invitation</AlertDialog.Title>
			<AlertDialog.Description>
				Are you sure you want to cancel the invitation for <strong class="text-foreground"
					>{invitationToCancel?.email}</strong
				>? The invitation link will be deactivated.
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>Cancel</AlertDialog.Cancel>
			<Button variant="destructive" onclick={cancelInvitation}>Cancel Invitation</Button>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>

<style>
	:global(td) {
		white-space: nowrap;
	}
</style>
