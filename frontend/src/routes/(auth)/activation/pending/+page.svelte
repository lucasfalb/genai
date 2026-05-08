<script lang="ts">
	import { page } from '$app/state';
	import MailCheck from '@lucide/svelte/icons/mail-check';
	import Send from '@lucide/svelte/icons/send';
	import { authApi } from '$lib/api/auth';
	import { getErrorMessage } from '$lib/api/client';
	import { toast } from 'svelte-sonner';

	const email = $derived(page.url.searchParams.get('email') ?? '');
	let loading = $state(false);
	let resent = $state(false);

	async function resendActivation() {
		if (!email) {
			toast.error('Email is required to resend the activation link.');
			return;
		}
		loading = true;
		try {
			await authApi.activationRequest({ email });
			resent = true;
			toast.success('Activation email sent again.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Failed to resend activation email.'));
		} finally {
			loading = false;
		}
	}
</script>

<div class="mb-7">
	<h2 class="font-display text-2xl font-semibold tracking-tight" style="color:var(--text-main)">Check your email</h2>
	<p class="mt-1.5 text-sm text-muted-foreground">Your account was created and the activation link was sent automatically.</p>
</div>

<div class="auth-card rounded-xl p-7">
	<div class="flex flex-col items-center gap-4 py-4 text-center">
		<div class="flex h-14 w-14 items-center justify-center rounded-full bg-blue-500/10">
			<MailCheck class="h-7 w-7 text-blue-500" />
		</div>
		<div>
			<p class="font-display font-semibold" style="color:var(--text-main)">Confirm your email to continue</p>
			{#if email}
				<p class="mt-1 text-sm text-muted-foreground">We sent the activation link to <strong class="text-foreground">{email}</strong>.</p>
			{:else}
				<p class="mt-1 text-sm text-muted-foreground">Open the activation link in your inbox to finish account setup.</p>
			{/if}
		</div>
		<p class="text-xs leading-relaxed text-muted-foreground">
			You can sign in after the account is activated. If the email does not arrive after a few minutes, request a new link.
		</p>
		{#if email}
			<button
				type="button"
				onclick={resendActivation}
				disabled={loading}
				class="inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold text-blue-500 transition-colors hover:bg-blue-500/10 disabled:opacity-60"
			>
				<Send class="h-4 w-4" />
				{loading ? 'Sending...' : resent ? 'Send again' : 'Resend activation link'}
			</button>
		{/if}
	</div>
</div>

<p class="mt-5 text-center text-sm text-muted-foreground">
	Already activated?
	<a href="/login" class="font-semibold text-blue-500 transition-colors hover:text-blue-400">Sign in</a>
</p>
