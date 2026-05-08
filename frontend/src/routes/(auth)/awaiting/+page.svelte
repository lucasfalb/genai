<script lang="ts">
	import { goto } from '$app/navigation';
	import Clock from '@lucide/svelte/icons/clock';
	import LogOut from '@lucide/svelte/icons/log-out';
	import { authApi } from '$lib/api/auth';
	import { authStore } from '$lib/stores/auth.svelte';
	import { toast } from 'svelte-sonner';

	let { data } = $props();
	const user = $derived(data.user);

	$effect(() => {
		authStore.user = data.user;
		if (data.accessToken && data.refreshToken) {
			authStore.setTokens(data.accessToken, data.refreshToken);
		}
	});

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
				An administrator needs to add you to a workspace before you can continue. Check back later or
				contact your team.
			</p>
		</div>
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
