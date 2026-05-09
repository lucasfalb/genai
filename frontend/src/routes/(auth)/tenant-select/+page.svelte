<script lang="ts">
	import { goto } from '$app/navigation';
	import Building2 from '@lucide/svelte/icons/building-2';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import LogOut from '@lucide/svelte/icons/log-out';
	import { authApi } from '$lib/api/auth';
	import { authStore } from '$lib/stores/auth.svelte';
	import { tenantStore } from '$lib/stores/tenant.svelte';
	import { tenantPath } from '$lib/routes/tenant';
	import { toast } from 'svelte-sonner';

	let { data } = $props();
	const memberships = $derived(data.memberships);

	$effect(() => {
		authStore.user = data.user;
		authStore.memberships = data.memberships;
		if (data.refreshToken) {
			authStore.setTokens(data.accessToken, data.refreshToken);
		}
	});

	function select(m: (typeof memberships)[number]) {
		console.log('[tenant-select] selected:', m.tenant_id, m.tenant_slug, m.tenant_name);
		tenantStore.setActiveTenant(m);
		const url = tenantPath(m, '/dashboard');
		console.log('[tenant-select] cookie after set:', document.cookie);
		console.log('[tenant-select] navigating to:', url);
		goto(url);
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
			tenantStore.clearTenant();
			await goto('/login');
		}
	}

	const ROLE_LABEL: Record<string, string> = {
		superadmin: 'Superadmin',
		owner: 'Owner',
		admin: 'Admin',
		tenant_admin: 'Admin',
		member: 'Member',
		viewer: 'Viewer'
	};
</script>

<div class="mb-7">
	<h2 class="font-display text-2xl font-semibold tracking-tight" style="color:var(--text-main)">
		Select workspace
	</h2>
	<p class="mt-1.5 text-sm text-muted-foreground">
		Choose the tenant you want to work in.
	</p>
</div>

<div class="auth-card rounded-xl p-3">
	{#if memberships.length === 0}
		<div class="flex flex-col items-center gap-3 px-4 py-8 text-center">
			<div class="flex h-12 w-12 items-center justify-center rounded-full bg-amber-500/10">
				<Building2 class="h-6 w-6 text-amber-500" />
			</div>
			<div>
				<p class="font-display font-semibold" style="color:var(--text-main)">No workspaces yet</p>
				<p class="mt-1 text-sm text-muted-foreground">
					Your account is pending tenant assignment. Contact your administrator.
				</p>
			</div>
		</div>
	{:else}
		{#each memberships as m (m.tenant_id)}
			<button
				onclick={() => select(m)}
				class="group flex w-full items-center gap-3.5 rounded-lg px-4 py-3.5 text-left transition-colors hover:bg-white/5"
			>
				<div
					class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-sm font-bold text-white"
					style="background:linear-gradient(135deg,rgba(59,130,246,0.5),rgba(139,92,246,0.4))"
				>
					{m.tenant_name.charAt(0).toUpperCase()}
				</div>
				<div class="min-w-0 flex-1">
					<p class="truncate text-sm font-semibold" style="color:var(--text-main)">{m.tenant_name}</p>
					<p class="text-[11px] text-muted-foreground">{ROLE_LABEL[m.role] ?? m.role}</p>
				</div>
				<ChevronRight class="h-4 w-4 shrink-0 text-muted-foreground/40 transition-transform group-hover:translate-x-0.5" />
			</button>
		{/each}
	{/if}
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
