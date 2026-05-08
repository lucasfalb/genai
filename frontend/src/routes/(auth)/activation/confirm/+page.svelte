<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import CheckCircle from '@lucide/svelte/icons/check-circle';
	import XCircle from '@lucide/svelte/icons/x-circle';
	import { goto } from '$app/navigation';
	import { authApi } from '$lib/api/auth';
	import { getErrorMessage } from '$lib/api/client';
	import { toast } from 'svelte-sonner';

	let loading = $state(true);
	let confirmed = $state(false);
	let error = $state('');

	onMount(async () => {
		const token = page.url.searchParams.get('token');
		if (!token) {
			error = 'No activation token found. Please use the link from your email.';
			toast.error(error);
			loading = false;
			return;
		}
		try {
			await authApi.activationConfirm({ token });
			confirmed = true;
			toast.success('Account activated. You can sign in now.');
		} catch (err) {
			error = getErrorMessage(err, 'Activation failed. The link may have expired.');
			toast.error(error);
		} finally {
			loading = false;
		}
	});
</script>

<div class="mb-7">
	<h2 class="font-display text-2xl font-semibold tracking-tight" style="color:var(--text-main)">Account activation</h2>
	<p class="mt-1.5 text-sm text-muted-foreground">Verifying your activation link…</p>
</div>

<div class="auth-card rounded-xl p-7">
	{#if loading}
		<div class="flex flex-col items-center gap-3 py-6 text-center">
			<div class="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"></div>
			<p class="text-sm text-muted-foreground">Activating your account…</p>
		</div>

	{:else if confirmed}
		<div class="flex flex-col items-center gap-3 py-4 text-center">
			<div class="flex h-12 w-12 items-center justify-center rounded-full bg-blue-500/10">
				<CheckCircle class="h-6 w-6 text-blue-500" />
			</div>
			<div>
				<p class="font-display font-semibold" style="color:var(--text-main)">Account activated!</p>
				<p class="mt-1 text-sm text-muted-foreground">Your account is ready to use.</p>
			</div>
			<a href="/login" class="auth-submit-btn mt-1 inline-flex items-center gap-2 rounded-lg px-5 py-2 text-sm font-semibold text-white">
				Go to login
			</a>
		</div>

	{:else}
		<div class="flex flex-col items-center gap-3 py-4 text-center">
			<div class="flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10">
				<XCircle class="h-6 w-6 text-red-500" />
			</div>
			<div>
				<p class="font-display font-semibold" style="color:var(--text-main)">Activation failed</p>
				<p class="mt-1 text-sm text-muted-foreground">{error}</p>
			</div>
			<a href="/activation/request" class="auth-submit-btn mt-1 inline-flex items-center gap-2 rounded-lg px-5 py-2 text-sm font-semibold text-white">
				<ShieldCheck class="h-4 w-4" />
				Request new link
			</a>
		</div>
	{/if}
</div>

<p class="mt-5 text-center text-sm text-muted-foreground">
	Already activated?
	<a href="/login" class="font-semibold text-blue-500 transition-colors hover:text-blue-400">Sign in</a>
</p>
