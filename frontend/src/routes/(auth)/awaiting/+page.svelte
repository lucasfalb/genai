<script lang="ts">
	import { goto } from '$app/navigation';
	import Clock from '@lucide/svelte/icons/clock';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import LogOut from '@lucide/svelte/icons/log-out';
	import type { TenantAccessResponse } from '$lib/api/types';
	import { authApi } from '$lib/api/auth';
	import { tenantStore } from '$lib/stores/tenant.svelte';
	import { authStore } from '$lib/stores/auth.svelte';
	import { tenantPath } from '$lib/routes/tenant';
	import { toast } from 'svelte-sonner';

	let { data } = $props();
	const user = $derived(data.user);
	let checking = $state(false);

	$effect(() => {
		authStore.user = data.user;
		if (data.accessToken && data.refreshToken) {
			authStore.setTokens(data.accessToken, data.refreshToken);
		}
	});

	async function checkAccess() {
		if (checking) return;
		if (!authStore.isAuthenticated) {
			toast.error('Session expired. Please sign in again.');
			await goto('/login');
			return;
		}
		checking = true;
		try {
			const apiBase = import.meta.env.PUBLIC_API_BASE_URL;
			let token = authStore.accessToken;

			const fetchTenants = (bearer: string) =>
				fetch(`${apiBase}/auth/me/tenants`, {
					headers: { Authorization: `Bearer ${bearer}`, 'Content-Type': 'application/json' }
				});

			let res = await fetchTenants(token);

			// Auto-refresh on 401
			if (res.status === 401 && authStore.refreshToken) {
				const refreshRes = await fetch(`${apiBase}/auth/refresh`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ refresh_token: authStore.refreshToken })
				});
				if (refreshRes.ok) {
					const refreshJson = await refreshRes.json();
					authStore.setTokens(refreshJson.data.access_token, refreshJson.data.refresh_token);
					token = authStore.accessToken;
					res = await fetchTenants(token);
				}
			}

			if (res.status === 401) {
				toast.error('Session expired. Please sign in again.');
				await goto('/login');
				return;
			}

			if (!res.ok) {
				toast.error('Could not verify access. Please try again.');
				return;
			}

			const json = await res.json();
			const memberships: TenantAccessResponse[] = json.data;
			if (memberships.length === 1) {
				tenantStore.setActiveTenant(memberships[0]);
				toast.success('Access granted! Redirecting...');
				await goto(tenantPath(memberships[0], '/dashboard'));
				return;
			}
			if (memberships.length > 1) {
				toast.success('Access granted!');
				await goto('/tenant-select');
				return;
			}
			toast.info('Still pending. Try again later.');
		} catch {
			toast.error('Could not verify access. Please try again.');
		} finally {
			checking = false;
		}
	}

	async function logout() {
		try {
			if (authStore.refreshToken) {
				await authApi.logout({ refresh_token: authStore.refreshToken });
			}
			toast.success('Signed out.');
		} catch {
			toast.warning('Session cleared locally.');
		} finally {
			authStore.clearAuth();
			await goto('/login');
		}
	}
</script>

<div class="mb-7">
	<h2 class="font-display text-2xl font-semibold tracking-tight" style="color:var(--text-main)">
		Awaiting access
	</h2>
	<p class="mt-1.5 text-sm text-muted-foreground">
		Your account has been created successfully.
	</p>
</div>

<div class="auth-card rounded-xl p-7">
	<div class="flex flex-col items-center gap-4 py-4 text-center">
		<div class="flex h-14 w-14 items-center justify-center rounded-full bg-amber-500/10">
			<Clock class="h-7 w-7 text-amber-500" />
		</div>
		<div>
			<p class="font-display text-base font-semibold" style="color:var(--text-main)">
				Pending tenant assignment
			</p>
			{#if user}
				<p class="mt-1 text-sm text-muted-foreground">
					Logged in as <strong class="text-foreground">{user.email}</strong>
				</p>
			{/if}
			<p class="mt-3 max-w-xs text-sm text-muted-foreground">
				An administrator needs to add you to a workspace before you can continue.
			</p>
		</div>

		<button
			onclick={checkAccess}
			disabled={checking}
			class="mt-2 flex w-full items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-semibold tracking-wide text-white transition-all active:scale-[0.98] disabled:opacity-60"
			style="background:linear-gradient(135deg,rgba(59,130,246,0.8),rgba(99,102,241,0.7))"
		>
			<RefreshCw class="h-4 w-4 {checking ? 'animate-spin' : ''}" />
			{checking ? 'Checking...' : 'Check access'}
		</button>
	</div>
</div>

<p class="mt-5 text-center">
	<button
		onclick={logout}
		class="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
	>
		<LogOut class="h-3.5 w-3.5" />
		Sign out
	</button>
</p>
