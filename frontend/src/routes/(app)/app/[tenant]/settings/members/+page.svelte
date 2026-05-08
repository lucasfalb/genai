<script lang="ts">
	import RoleBadge from '$lib/components/RoleBadge.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { membersApi } from '$lib/api/members';
	import { invitationsApi } from '$lib/api/invitations';
	import { ApiError, getErrorMessage } from '$lib/api/client';
	import type { TenantInvitationResponse, TenantMemberResponse } from '$lib/api/types';
	import Shield from '@lucide/svelte/icons/shield';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import MailPlus from '@lucide/svelte/icons/mail-plus';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import X from '@lucide/svelte/icons/x';
	import { toast } from 'svelte-sonner';

	let { data } = $props();

	let members = $state<TenantMemberResponse[]>(data.members);
	let invitations = $state<TenantInvitationResponse[]>(data.invitations);
	let busyUserId = $state('');
	let email = $state('');
	let inviteRole = $state('member');
	let creating = $state(false);
	let busyInvitationId = $state('');

	const ASSIGNABLE_ROLES = ['tenant_admin', 'member', 'viewer'];
	const ASSIGNABLE_STATUS = ['active', 'pending', 'suspended'];

	function initials(member: TenantMemberResponse): string {
		const source = member.name || member.email;
		return source
			.split(/[\s@.]+/)
			.filter(Boolean)
			.slice(0, 2)
			.map((part) => part[0]?.toUpperCase())
			.join('');
	}

	function canEdit(member: TenantMemberResponse): boolean {
		return member.user_id !== data.currentUserId && member.role !== 'owner' && member.role !== 'superadmin';
	}

	async function updateMember(member: TenantMemberResponse, patch: { role?: string; status?: string }) {
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

	async function removeMember(member: TenantMemberResponse) {
		if (!canEdit(member)) return;
		if (!confirm(`Remove ${member.email} from this tenant?`)) return;
		busyUserId = member.user_id;
		try {
			await membersApi.remove(member.user_id);
			members = members.filter((item) => item.user_id !== member.user_id);
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
		if (invitation.status === 'pending' && new Date(invitation.expires_at).getTime() <= Date.now()) {
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

	async function cancelInvitation(invitation: TenantInvitationResponse) {
		if (!confirm(`Cancel invitation for ${invitation.email}?`)) return;
		busyInvitationId = invitation.id;
		try {
			await invitationsApi.cancel(invitation.id);
			invitations = invitations.filter((item) => item.id !== invitation.id);
			toast.success('Invitation cancelled.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Invitation cancel failed.'));
		} finally {
			busyInvitationId = '';
		}
	}
</script>

<div class="mx-auto max-w-6xl space-y-6 p-6">
	<div class="flex items-center justify-between gap-4">
		<div>
			<h1 class="font-display text-xl font-semibold" style="color:var(--text-main)">Members</h1>
			<p class="mt-1 text-sm text-muted-foreground">Tenant users, roles and membership status</p>
		</div>
		<div class="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
			<Shield class="h-5 w-5" />
		</div>
	</div>

	<section class="rounded-xl" style="background:var(--surface);border:1px solid var(--ds-border)">
		{#if members.length === 0}
			<p class="py-12 text-center text-sm text-muted-foreground">No tenant members found.</p>
		{:else}
			<div class="overflow-x-auto">
				<table class="w-full text-left text-sm">
					<thead class="border-b text-xs uppercase tracking-widest text-muted-foreground" style="border-color:var(--ds-border)">
						<tr>
							<th class="px-4 py-3 font-semibold">User</th>
							<th class="px-4 py-3 font-semibold">Role</th>
							<th class="px-4 py-3 font-semibold">Status</th>
							<th class="px-4 py-3 text-right font-semibold">Actions</th>
						</tr>
					</thead>
					<tbody>
						{#each members as member (member.user_id)}
							{@const isSelf = member.user_id === data.currentUserId}
							{@const editable = canEdit(member)}
							{@const busy = busyUserId === member.user_id}
							<tr class="border-b last:border-b-0" style="border-color:var(--ds-border)">
								<td class="px-4 py-3">
									<div class="flex items-center gap-3">
										<div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-800 text-xs font-semibold text-white" style="border:1px solid var(--ds-border-hover)">
											{initials(member)}
										</div>
										<div class="min-w-0">
											<p class="truncate font-medium" style="color:var(--text-main)">
												{member.name || member.email}
												{#if isSelf}<span class="ml-2 text-xs text-muted-foreground">(you)</span>{/if}
											</p>
											<p class="truncate text-xs text-muted-foreground">{member.email}</p>
										</div>
									</div>
								</td>
								<td class="px-4 py-3">
									{#if editable}
										<select
											value={member.role}
											disabled={busy}
											onchange={(event) => updateMember(member, { role: event.currentTarget.value })}
											class="auth-input rounded-lg px-3 py-1.5 text-xs"
										>
											{#each ASSIGNABLE_ROLES as role (role)}
												<option value={role}>{role}</option>
											{/each}
										</select>
									{:else}
										<RoleBadge role={member.role} />
									{/if}
								</td>
								<td class="px-4 py-3">
									{#if editable}
										<select
											value={member.status}
											disabled={busy}
											onchange={(event) => updateMember(member, { status: event.currentTarget.value })}
											class="auth-input rounded-lg px-3 py-1.5 text-xs"
										>
											{#each ASSIGNABLE_STATUS as status (status)}
												<option value={status}>{status}</option>
											{/each}
										</select>
									{:else}
										<StatusBadge status={member.status} />
									{/if}
								</td>
								<td class="px-4 py-3 text-right">
									<button
										onclick={() => removeMember(member)}
										disabled={!editable || busy}
										class="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-red-400 transition-colors hover:bg-red-400/10 disabled:cursor-not-allowed disabled:opacity-40"
									>
										<Trash2 class="h-3.5 w-3.5" />
										Remove
									</button>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</section>

	<section class="rounded-xl p-5" style="background:var(--surface);border:1px solid var(--ds-border)">
		<div class="mb-4 flex items-center justify-between gap-4">
			<div>
				<h2 class="font-display text-sm font-semibold" style="color:var(--text-main)">Invitations</h2>
				<p class="mt-1 text-sm text-muted-foreground">Invite users into this tenant.</p>
			</div>
			<div class="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
				<MailPlus class="h-5 w-5" />
			</div>
		</div>

		<div class="grid gap-3 md:grid-cols-[1fr_180px_auto]">
			<div class="space-y-1.5">
				<label for="invite-email" class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Email</label>
				<input id="invite-email" type="email" bind:value={email} class="auth-input w-full rounded-lg px-3.5 py-2.5 text-sm" placeholder="name@company.com" />
			</div>
			<div class="space-y-1.5">
				<label for="invite-role" class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Role</label>
				<select id="invite-role" bind:value={inviteRole} class="auth-input w-full rounded-lg px-3.5 py-2.5 text-sm">
					{#each ASSIGNABLE_ROLES as option (option)}
						<option value={option}>{option}</option>
					{/each}
				</select>
			</div>
			<div class="flex items-end">
				<button onclick={createInvitation} disabled={creating} class="h-[42px] rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:opacity-60">
					{creating ? 'Inviting...' : 'Invite'}
				</button>
			</div>
		</div>
	</section>

	<section class="rounded-xl" style="background:var(--surface);border:1px solid var(--ds-border)">
		{#if invitations.length === 0}
			<p class="py-10 text-center text-sm text-muted-foreground">No pending invitations.</p>
		{:else}
			<div class="overflow-x-auto">
				<table class="w-full text-left text-sm">
					<thead class="border-b text-xs uppercase tracking-widest text-muted-foreground" style="border-color:var(--ds-border)">
						<tr>
							<th class="px-4 py-3 font-semibold">Email</th>
							<th class="px-4 py-3 font-semibold">Role</th>
							<th class="px-4 py-3 font-semibold">Status</th>
							<th class="px-4 py-3 font-semibold">Expires</th>
							<th class="px-4 py-3 text-right font-semibold">Actions</th>
						</tr>
					</thead>
					<tbody>
						{#each invitations as invitation (invitation.id)}
							{@const status = effectiveStatus(invitation)}
							{@const busy = busyInvitationId === invitation.id}
							<tr class="border-b last:border-b-0" style="border-color:var(--ds-border)">
								<td class="px-4 py-3 font-medium" style="color:var(--text-main)">{invitation.email}</td>
								<td class="px-4 py-3"><RoleBadge role={invitation.role} /></td>
								<td class="px-4 py-3"><StatusBadge {status} /></td>
								<td class="px-4 py-3 text-xs text-muted-foreground">{formatExpiry(invitation.expires_at)}</td>
								<td class="px-4 py-3 text-right">
									<div class="flex justify-end gap-2">
										<button onclick={() => resendInvitation(invitation)} disabled={busy || status === 'accepted'} class="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-blue-400 transition-colors hover:bg-blue-400/10 disabled:opacity-40">
											<RefreshCw class="h-3.5 w-3.5" /> Resend
										</button>
										<button onclick={() => cancelInvitation(invitation)} disabled={busy || status !== 'pending'} class="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-red-400 transition-colors hover:bg-red-400/10 disabled:opacity-40">
											<X class="h-3.5 w-3.5" /> Cancel
										</button>
									</div>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</section>
</div>
