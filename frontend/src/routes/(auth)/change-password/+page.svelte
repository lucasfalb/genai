<script lang="ts">
	import Lock from '@lucide/svelte/icons/lock';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import CheckCircle from '@lucide/svelte/icons/check-circle';

	let current = $state('');
	let password = $state('');
	let confirm = $state('');
	let loading = $state(false);
	let done = $state(false);
	let error = $state('');

	import { authApi } from '$lib/api/auth';
	import { getErrorMessage } from '$lib/api/client';
	import { toast } from 'svelte-sonner';

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!current || !password || !confirm) { error = 'Please fill in all fields.'; return; }
		if (password !== confirm) { error = 'New passwords do not match.'; return; }
		if (password.length < 8) { error = 'New password must be at least 8 characters.'; return; }
		if (current === password) { error = 'New password must differ from current.'; return; }
		error = '';
		loading = true;
		try {
			await authApi.passwordChange({ current_password: current, new_password: password });
			done = true;
			toast.success('Password changed successfully.');
		} catch (err) {
			error = getErrorMessage(err, 'Password change failed. Please try again.');
			toast.error(error);
		} finally {
			loading = false;
		}
	}
</script>

<div class="mb-7">
	<h2 class="font-display text-2xl font-semibold tracking-tight" style="color:var(--text-main)">Change password</h2>
	<p class="mt-1.5 text-sm text-muted-foreground">Confirm your current password and set a new one.</p>
</div>

<div class="auth-card rounded-xl p-7">
	{#if done}
		<div class="flex flex-col items-center gap-3 py-4 text-center">
			<div class="flex h-12 w-12 items-center justify-center rounded-full bg-blue-500/10">
				<CheckCircle class="h-6 w-6 text-blue-500" />
			</div>
			<div>
				<p class="font-display font-semibold" style="color:var(--text-main)">Password changed!</p>
				<p class="mt-1 text-sm text-muted-foreground">Your password has been updated successfully.</p>
			</div>
		</div>
	{:else}
		<form onsubmit={handleSubmit} class="flex flex-col gap-4">
			{#if error}
				<div class="rounded-lg px-3 py-2.5 text-xs font-medium text-red-500" style="background:color-mix(in srgb,red 8%,transparent);border:1px solid color-mix(in srgb,red 18%,transparent)">{error}</div>
			{/if}
			<div class="flex flex-col gap-1.5">
				<label class="font-display block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Current password</label>
				<div class="relative">
					<Lock class="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/50" />
					<input type="password" bind:value={current} placeholder="Your current password" autocomplete="current-password"
						class="auth-input rounded-lg py-2.5 pr-4 pl-9 text-sm" />
				</div>
			</div>
			<div class="h-px" style="background:var(--border)"></div>
			<div class="flex flex-col gap-1.5">
				<label class="font-display block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">New password</label>
				<div class="relative">
					<Lock class="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/50" />
					<input type="password" bind:value={password} placeholder="Min. 8 characters" autocomplete="new-password"
						class="auth-input rounded-lg py-2.5 pr-4 pl-9 text-sm" />
				</div>
			</div>
			<div class="flex flex-col gap-1.5">
				<label class="font-display block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Confirm new password</label>
				<div class="relative">
					<Lock class="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/50" />
					<input type="password" bind:value={confirm} placeholder="Repeat new password" autocomplete="new-password"
						class="auth-input rounded-lg py-2.5 pr-4 pl-9 text-sm" />
				</div>
			</div>
			<button type="submit" disabled={loading}
				class="auth-submit-btn flex w-full items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-semibold tracking-wide text-white transition-all active:scale-[0.98] disabled:opacity-60">
				<ShieldCheck class="h-4 w-4" />
				{loading ? 'Saving...' : 'Change password'}
			</button>
		</form>
	{/if}
</div>

<p class="mt-5 text-center text-sm text-muted-foreground">
	<a href="/login" class="font-semibold text-blue-500 transition-colors hover:text-blue-400">Back to login</a>
</p>
