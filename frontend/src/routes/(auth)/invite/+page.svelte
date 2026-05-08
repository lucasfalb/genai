<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import Mail from '@lucide/svelte/icons/mail';
	import Lock from '@lucide/svelte/icons/lock';
	import User from '@lucide/svelte/icons/user';
	import UserCheck from '@lucide/svelte/icons/user-check';
	import CheckCircle from '@lucide/svelte/icons/check-circle';
	import AlertTriangle from '@lucide/svelte/icons/alert-triangle';
	import { invitationsPublicApi } from '$lib/api/invitations';
	import { ApiError } from '$lib/api/client';
	import type { TenantInvitationPublicResponse } from '$lib/api/types';

	const token = $derived(page.url.searchParams.get('token') ?? '');

	let invite = $state<TenantInvitationPublicResponse | null>(null);
	let validating = $state(true);
	let tokenError = $state('');

	let name = $state('');
	let password = $state('');
	let loading = $state(false);
	let done = $state(false);
	let error = $state('');

	onMount(async () => {
		if (!token) {
			tokenError = 'No invitation token found.';
			validating = false;
			return;
		}
		try {
			invite = await invitationsPublicApi.validate({ token });
		} catch (err) {
			tokenError = err instanceof ApiError ? err.message : 'Invalid or expired invitation link.';
		} finally {
			validating = false;
		}
	});

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!invite) return;
		if (!name) { error = 'Please enter your name.'; return; }
		if (!password) { error = 'Please set a password.'; return; }
		if (password.length < 8) { error = 'Password must be at least 8 characters.'; return; }
		error = '';
		loading = true;
		try {
			await invitationsPublicApi.accept({
				token,
				email: invite.email,
				name,
				password
			});
			done = true;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Failed to accept invitation.';
		} finally {
			loading = false;
		}
	}
</script>

<div class="mb-7">
	<h2 class="font-display text-2xl font-semibold tracking-tight" style="color:var(--text-main)">
		Join workspace
	</h2>
	<p class="mt-1.5 text-sm text-muted-foreground">Accept your invitation to get started.</p>
</div>

<div class="auth-card rounded-xl p-7">
	{#if validating}
		<div class="flex items-center justify-center py-8">
			<div class="h-6 w-6 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"></div>
		</div>

	{:else if tokenError}
		<div class="flex flex-col items-center gap-3 py-4 text-center">
			<div class="flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10">
				<AlertTriangle class="h-6 w-6 text-red-500" />
			</div>
			<div>
				<p class="font-display font-semibold" style="color:var(--text-main)">Invalid invitation</p>
				<p class="mt-1 text-sm text-muted-foreground">{tokenError}</p>
			</div>
		</div>

	{:else if done}
		<div class="flex flex-col items-center gap-3 py-4 text-center">
			<div class="flex h-12 w-12 items-center justify-center rounded-full bg-blue-500/10">
				<CheckCircle class="h-6 w-6 text-blue-500" />
			</div>
			<div>
				<p class="font-display font-semibold" style="color:var(--text-main)">Welcome aboard!</p>
				<p class="mt-1 text-sm text-muted-foreground">
					Your account is ready. Sign in to access <strong class="text-foreground">{invite?.tenant_name}</strong>.
				</p>
			</div>
			<a
				href="/login"
				class="auth-submit-btn mt-1 inline-flex items-center gap-2 rounded-lg px-5 py-2 text-sm font-semibold text-white"
			>
				Go to login
			</a>
		</div>

	{:else if invite}
		<!-- Invite details -->
		<div
			class="mb-5 flex items-center gap-3 rounded-lg px-4 py-3"
			style="background:rgba(59,130,246,0.07);border:1px solid rgba(59,130,246,0.15)"
		>
			<div
				class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-sm font-bold text-white"
				style="background:linear-gradient(135deg,rgba(59,130,246,0.5),rgba(139,92,246,0.4))"
			>
				{invite.tenant_name.charAt(0).toUpperCase()}
			</div>
			<div class="min-w-0">
				<p class="truncate text-sm font-semibold text-blue-400">{invite.tenant_name}</p>
				<p class="text-[11px] text-muted-foreground">Invited as <span class="capitalize">{invite.role}</span></p>
			</div>
		</div>

		<form onsubmit={handleSubmit} class="flex flex-col gap-4">
			{#if error}
				<div
					class="rounded-lg px-3 py-2.5 text-xs font-medium text-red-500"
					style="background:color-mix(in srgb,red 8%,transparent);border:1px solid color-mix(in srgb,red 18%,transparent)"
				>{error}</div>
			{/if}

			<div class="flex flex-col gap-1.5">
				<label class="font-display block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Email</label>
				<div class="relative">
					<Mail class="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/50" />
					<input
						type="email"
						value={invite.email}
						disabled
						class="auth-input rounded-lg py-2.5 pr-4 pl-9 text-sm opacity-60"
					/>
				</div>
			</div>

			<div class="flex flex-col gap-1.5">
				<label class="font-display block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Your name</label>
				<div class="relative">
					<User class="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/50" />
					<input
						type="text"
						bind:value={name}
						placeholder="Full name"
						autocomplete="name"
						class="auth-input rounded-lg py-2.5 pr-4 pl-9 text-sm"
					/>
				</div>
			</div>

			<div class="flex flex-col gap-1.5">
				<label class="font-display block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Password</label>
				<div class="relative">
					<Lock class="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/50" />
					<input
						type="password"
						bind:value={password}
						placeholder="Min. 8 characters"
						autocomplete="new-password"
						class="auth-input rounded-lg py-2.5 pr-4 pl-9 text-sm"
					/>
				</div>
			</div>

			<button
				type="submit"
				disabled={loading}
				class="auth-submit-btn flex w-full items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-semibold tracking-wide text-white transition-all active:scale-[0.98] disabled:opacity-60"
			>
				<UserCheck class="h-4 w-4" />
				{loading ? 'Joining...' : 'Accept invitation'}
			</button>
		</form>
	{/if}
</div>

<p class="mt-5 text-center text-sm text-muted-foreground">
	<a href="/login" class="font-semibold text-blue-500 transition-colors hover:text-blue-400">
		Already have an account? Sign in
	</a>
</p>
