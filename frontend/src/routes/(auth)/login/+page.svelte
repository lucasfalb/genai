<script lang="ts">
	import { onMount } from 'svelte';
	import Mail from '@lucide/svelte/icons/mail';
	import Lock from '@lucide/svelte/icons/lock';
	import LogIn from '@lucide/svelte/icons/log-in';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { authApi } from '$lib/api/auth';
	import { authStore } from '$lib/stores/auth.svelte';
	import { tenantStore } from '$lib/stores/tenant.svelte';
	import { tenantPath } from '$lib/routes/tenant';
	import { getErrorMessage } from '$lib/api/client';
	import { toast } from 'svelte-sonner';

	let email = $state('');
	let password = $state('');
	let remember = $state(false);
	let loading = $state(false);
	let error = $state('');
	let { data } = $props();

	onMount(() => {
		if (page.url.searchParams.get('expired') === '1') {
			authStore.clearAuth();
			tenantStore.clearTenant();
			error = 'Your session expired. Please sign in again.';
		}
	});

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!email || !password) { error = 'Please fill in all fields.'; return; }
		error = '';
		loading = true;
		try {
			const auth = await authApi.login({ email, password });

			if (auth.awaiting_assignment || !auth.access_token || !auth.refresh_token) {
				authStore.clearAuth();
				toast.info('Account authenticated, but no tenant is assigned yet.');
				await goto('/awaiting');
				return;
			}

			authStore.setTokens(auth.access_token, auth.refresh_token);
			const user = await authApi.me();
			const memberships = await authApi.myTenants();
			authStore.user = user;
			authStore.memberships = memberships;

			if (memberships.length === 0 && user.is_superadmin) {
				toast.success('Signed in successfully.');
				await goto('/tenant-select');
				return;
			}

			if (memberships.length === 0) {
				toast.info('Account authenticated, but no tenant is assigned yet.');
				await goto('/awaiting');
				return;
			}
			tenantStore.loadFromLocalStorage(memberships);
			if (!tenantStore.activeTenantId && memberships.length === 1) {
				tenantStore.setActiveTenant(memberships[0]);
			}
			toast.success('Signed in successfully.');
			await goto(
				memberships.length > 1 && !tenantStore.activeTenantId
					? '/tenant-select'
					: tenantPath(memberships.find((membership) => membership.tenant_id === tenantStore.activeTenantId) ?? memberships[0], '/dashboard')
			);
		} catch (err) {
			error = getErrorMessage(err, 'Login failed. Please try again.');
			toast.error(error);
		} finally {
			loading = false;
		}
	}
</script>

<div class="mb-8">
	<h2 class="font-display text-2xl font-semibold tracking-tight" style="color:var(--text-main)">Welcome back</h2>
	<p class="mt-1.5 text-sm text-muted-foreground">Sign in to your account to continue.</p>
</div>

<div class="auth-card rounded-xl p-7">
	<form onsubmit={handleSubmit} class="flex flex-col gap-4">
		{#if error}
			<div class="rounded-lg px-3 py-2.5 text-xs font-medium text-red-500" style="background:color-mix(in srgb,red 8%,transparent);border:1px solid color-mix(in srgb,red 18%,transparent)">{error}</div>
		{/if}

		<div class="flex flex-col gap-1.5">
			<label class="font-display block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Email</label>
			<div class="relative">
				<Mail class="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/50" />
				<input type="email" bind:value={email} placeholder="you@example.com" autocomplete="email"
					class="auth-input rounded-lg py-2.5 pr-4 pl-9 text-sm" />
			</div>
		</div>

		<div class="flex flex-col gap-1.5">
			<div class="flex items-center justify-between">
				<label class="font-display block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Password</label>
				<a href="/forgot-password" class="text-[11px] font-medium text-blue-500 transition-colors hover:text-blue-400">Forgot?</a>
			</div>
			<div class="relative">
				<Lock class="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/50" />
				<input type="password" bind:value={password} placeholder="••••••••" autocomplete="current-password"
					class="auth-input rounded-lg py-2.5 pr-4 pl-9 text-sm" />
			</div>
		</div>

		<label class="flex cursor-pointer items-center gap-2">
			<input type="checkbox" bind:checked={remember} class="h-4 w-4 rounded accent-blue-500" />
			<span class="text-xs text-muted-foreground">Keep me signed in</span>
		</label>

		<button type="submit" disabled={loading}
			class="auth-submit-btn mt-1 flex w-full items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-semibold tracking-wide text-white transition-all active:scale-[0.98] disabled:opacity-60">
			<LogIn class="h-4 w-4" />
			{loading ? 'Signing in...' : 'Sign in'}
		</button>
	</form>

	<div class="my-5 flex items-center gap-3">
		<span class="divider-line"></span>
		<span class="shrink-0 text-[10px] font-medium uppercase tracking-widest text-muted-foreground/50">or continue with</span>
		<span class="divider-line"></span>
	</div>

	<div class="grid grid-cols-2 gap-2.5">
		<button type="button" class="social-btn flex items-center justify-center gap-2 rounded-lg py-2 text-xs font-medium">
			<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none">
				<path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
				<path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
				<path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
				<path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
			</svg>
			Google
		</button>
		<button type="button" class="social-btn flex items-center justify-center gap-2 rounded-lg py-2 text-xs font-medium">
			<svg class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
				<path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
			</svg>
			GitHub
		</button>
	</div>
</div>

<p class="mt-5 text-center text-sm text-muted-foreground">
	{#if data.publicSettings.registration_enabled}
		New to the platform?
		<a href="/register" class="font-semibold text-blue-500 transition-colors hover:text-blue-400">Create an account</a>
	{:else}
		Account creation is currently disabled.
	{/if}
</p>
