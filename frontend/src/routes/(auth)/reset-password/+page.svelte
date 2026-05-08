<script lang="ts">
	import Lock from '@lucide/svelte/icons/lock';
	import KeyRound from '@lucide/svelte/icons/key-round';
	import CheckCircle from '@lucide/svelte/icons/check-circle';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import { page } from '$app/state';

	let password = $state('');
	let confirm = $state('');
	let loading = $state(false);
	let done = $state(false);
	let error = $state('');

	const token = $derived(page.url.searchParams.get('token') ?? '');

	import { authApi } from '$lib/api/auth';
	import { getErrorMessage } from '$lib/api/client';
	import { toast } from 'svelte-sonner';

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!password || !confirm) { error = 'Please fill in all fields.'; return; }
		if (password !== confirm) { error = 'Passwords do not match.'; return; }
		if (password.length < 8) { error = 'Password must be at least 8 characters.'; return; }
		error = '';
		loading = true;
		try {
			await authApi.passwordReset({ token, new_password: password });
			done = true;
			toast.success('Password updated. You can sign in now.');
		} catch (err) {
			error = getErrorMessage(err, 'Password reset failed. Please try again.');
			toast.error(error);
		} finally {
			loading = false;
		}
	}
</script>

<div class="mb-7">
	<h2 class="font-display text-2xl font-semibold tracking-tight" style="color:var(--text-main)">New password</h2>
	<p class="mt-1.5 text-sm text-muted-foreground">Choose a strong password for your account.</p>
</div>

<div class="auth-card rounded-xl p-7">
	{#if done}
		<div class="flex flex-col items-center gap-3 py-4 text-center">
			<div class="flex h-12 w-12 items-center justify-center rounded-full bg-blue-500/10">
				<CheckCircle class="h-6 w-6 text-blue-500" />
			</div>
			<div>
				<p class="font-display font-semibold" style="color:var(--text-main)">Password updated!</p>
				<p class="mt-1 text-sm text-muted-foreground">You can now sign in with your new password.</p>
			</div>
			<a href="/login" class="auth-submit-btn mt-1 inline-flex items-center gap-2 rounded-lg px-5 py-2 text-sm font-semibold text-white">
				Go to login
			</a>
		</div>
	{:else}
		{#if !token}
			<div class="mb-4 rounded-lg px-3 py-2.5 text-xs font-medium text-amber-500" style="background:color-mix(in srgb,orange 8%,transparent);border:1px solid color-mix(in srgb,orange 18%,transparent)">
				Invalid or expired link. Please request a new one.
			</div>
		{/if}
		<form onsubmit={handleSubmit} class="flex flex-col gap-4">
			{#if error}
				<div class="rounded-lg px-3 py-2.5 text-xs font-medium text-red-500" style="background:color-mix(in srgb,red 8%,transparent);border:1px solid color-mix(in srgb,red 18%,transparent)">{error}</div>
			{/if}
			<div class="flex flex-col gap-1.5">
				<label class="font-display block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">New password</label>
				<div class="relative">
					<Lock class="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/50" />
					<input type="password" bind:value={password} placeholder="Min. 8 characters" autocomplete="new-password"
						class="auth-input rounded-lg py-2.5 pr-4 pl-9 text-sm" />
				</div>
			</div>
			<div class="flex flex-col gap-1.5">
				<label class="font-display block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Confirm password</label>
				<div class="relative">
					<Lock class="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/50" />
					<input type="password" bind:value={confirm} placeholder="Repeat password" autocomplete="new-password"
						class="auth-input rounded-lg py-2.5 pr-4 pl-9 text-sm" />
				</div>
			</div>
			<button type="submit" disabled={loading || !token}
				class="auth-submit-btn flex w-full items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-semibold tracking-wide text-white transition-all active:scale-[0.98] disabled:opacity-60">
				<KeyRound class="h-4 w-4" />
				{loading ? 'Saving...' : 'Set new password'}
			</button>
		</form>
	{/if}
</div>

<p class="mt-5 text-center text-sm text-muted-foreground">
	<a href="/login" class="inline-flex items-center gap-1.5 font-semibold text-blue-500 transition-colors hover:text-blue-400">
		<ArrowLeft class="h-3.5 w-3.5" />Back to login
	</a>
</p>
