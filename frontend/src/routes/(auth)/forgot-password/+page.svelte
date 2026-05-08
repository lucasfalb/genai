<script lang="ts">
	import Mail from '@lucide/svelte/icons/mail';
	import Send from '@lucide/svelte/icons/send';
	import CheckCircle from '@lucide/svelte/icons/check-circle';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';

	let email = $state('');
	let loading = $state(false);
	let sent = $state(false);
	let error = $state('');

	import { authApi } from '$lib/api/auth';
	import { getErrorMessage } from '$lib/api/client';
	import { toast } from 'svelte-sonner';

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!email) { error = 'Please enter your email address.'; return; }
		error = '';
		loading = true;
		try {
			await authApi.passwordForgot({ email });
			sent = true;
			toast.success('Password reset email requested.');
		} catch (err) {
			error = getErrorMessage(err, 'Failed to send reset email.');
			toast.error(error);
		} finally {
			loading = false;
		}
	}
</script>

<div class="mb-7">
	<h2 class="font-display text-2xl font-semibold tracking-tight" style="color:var(--text-main)">Reset password</h2>
	<p class="mt-1.5 text-sm text-muted-foreground">Enter your email and we'll send reset instructions.</p>
</div>

<div class="auth-card rounded-xl p-7">
	{#if sent}
		<div class="flex flex-col items-center gap-3 py-4 text-center">
			<div class="flex h-12 w-12 items-center justify-center rounded-full bg-blue-500/10">
				<CheckCircle class="h-6 w-6 text-blue-500" />
			</div>
			<div>
				<p class="font-display font-semibold" style="color:var(--text-main)">Check your inbox</p>
				<p class="mt-1 text-sm text-muted-foreground">Reset instructions sent to <strong class="text-foreground">{email}</strong></p>
			</div>
		</div>
	{:else}
		<form onsubmit={handleSubmit} class="flex flex-col gap-4">
			{#if error}
				<div class="rounded-lg px-3 py-2.5 text-xs font-medium text-red-500" style="background:color-mix(in srgb,red 8%,transparent);border:1px solid color-mix(in srgb,red 18%,transparent)">{error}</div>
			{/if}
			<div class="flex flex-col gap-1.5">
				<label class="font-display block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Email address</label>
				<div class="relative">
					<Mail class="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/50" />
					<input type="email" bind:value={email} placeholder="you@example.com" autocomplete="email"
						class="auth-input rounded-lg py-2.5 pr-4 pl-9 text-sm" />
				</div>
			</div>
			<button type="submit" disabled={loading}
				class="auth-submit-btn flex w-full items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-semibold tracking-wide text-white transition-all active:scale-[0.98] disabled:opacity-60">
				<Send class="h-4 w-4" />
				{loading ? 'Sending...' : 'Send reset link'}
			</button>
		</form>
	{/if}
</div>

<p class="mt-5 text-center text-sm text-muted-foreground">
	<a href="/login" class="inline-flex items-center gap-1.5 font-semibold text-blue-500 transition-colors hover:text-blue-400">
		<ArrowLeft class="h-3.5 w-3.5" />Back to login
	</a>
</p>
