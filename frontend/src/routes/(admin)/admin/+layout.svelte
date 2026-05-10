<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import ModeToggle from '$lib/components/mode-toggle.svelte';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { authApi } from '$lib/api/auth';
	import { authStore } from '$lib/stores/auth.svelte';
	import { tenantStore } from '$lib/stores/tenant.svelte';
	import { toast } from 'svelte-sonner';
	import type { Component } from 'svelte';

	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Bell from '@lucide/svelte/icons/bell';
	import Building2 from '@lucide/svelte/icons/building-2';
	import Cpu from '@lucide/svelte/icons/cpu';
	import LayoutGrid from '@lucide/svelte/icons/layout-grid';
	import LogOut from '@lucide/svelte/icons/log-out';
	import Mail from '@lucide/svelte/icons/mail';
	import Settings from '@lucide/svelte/icons/settings';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import Users from '@lucide/svelte/icons/users';
	import Wrench from '@lucide/svelte/icons/wrench';

	let { data, children } = $props();

	$effect(() => {
		authStore.user = data.user;
		if (data.refreshToken) {
			authStore.setTokens(data.accessToken, data.refreshToken);
		}
		tenantStore.clearTenant();
	});

	interface NavItem {
		href: string;
		label: string;
		icon: Component;
		description: string;
		hideHeader?: boolean;
	}

	const navGroups: { label: string; items: NavItem[] }[] = [
		{
			label: 'Platform Control',
			items: [
				{
					href: '/admin',
					label: 'Overview',
					icon: LayoutGrid,
					description: 'Global platform summary',
					hideHeader: true
				},
				{
					href: '/admin/tenants',
					label: 'Tenants',
					icon: Building2,
					description: 'Tenant administration'
				},
				{
					href: '/admin/users',
					label: 'Users',
					icon: Users,
					description: 'Global user administration'
				}
			]
		},
		{
			label: 'Operations',
			items: [
				{
					href: '/admin/registry/skills',
					label: 'Skills',
					icon: Cpu,
					description: 'Skill registry definitions'
				},
				{
					href: '/admin/registry/tools',
					label: 'Tools',
					icon: Wrench,
					description: 'Tool registry definitions'
				},
				{
					href: '/admin/email-templates',
					label: 'Email Templates',
					icon: Mail,
					description: 'Transactional communication templates'
				},
				{
					href: '/admin/settings',
					label: 'Settings',
					icon: Settings,
					description: 'System-wide settings'
				}
			]
		}
	];

	const allNavItems = navGroups.flatMap((group) => group.items);
	const currentPath = $derived(page.url.pathname.replace(/\/$/, '') || '/admin');
	const currentNav = $derived(
		allNavItems.find((item) =>
			item.href === '/admin' ? currentPath === '/admin' : currentPath.startsWith(item.href)
		) ?? allNavItems[0]
	);

	function isActive(href: string): boolean {
		if (href === '/admin') return currentPath === '/admin';
		return currentPath === href || currentPath.startsWith(`${href}/`);
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
</script>

<svelte:head>
	<title>Superadmin - GENAI</title>
</svelte:head>

<div
	class="pointer-events-none fixed top-[-20%] left-[-10%] h-[600px] w-[600px] rounded-full bg-blue-600/10 blur-[150px]"
	style="z-index:0"
></div>
<div
	class="pointer-events-none fixed right-[-5%] bottom-[-10%] h-[500px] w-[500px] rounded-full bg-cyan-600/5 blur-[120px]"
	style="z-index:0"
></div>

<Sidebar.Provider
	class="h-screen overflow-hidden selection:bg-blue-500/30"
	style="position:relative;z-index:1"
>
	<Sidebar.Root
		collapsible="icon"
		class="glass-panel border-r"
		style="border-color:var(--ds-border)"
	>
		<Sidebar.Header
			class="h-16 shrink-0 flex-row items-center gap-2 border-b px-4"
			style="border-color:var(--ds-border)"
		>
			<ShieldAlert class="size-5 shrink-0 text-amber-400" />
			<div class="group-data-[collapsible=icon]:hidden">
				<p class="font-display text-lg font-semibold tracking-tight" style="color:var(--text-main)">
					Superadmin
				</p>
				<p class="text-[10px] tracking-widest text-muted-foreground uppercase">Platform Control</p>
			</div>
		</Sidebar.Header>

		<Sidebar.Content class="mt-1">
			{#each navGroups as group, groupIndex}
				{#if groupIndex > 0}<Sidebar.Separator />{/if}
				<Sidebar.Group>
					<Sidebar.GroupLabel
						class="font-display text-[10px] font-semibold tracking-widest uppercase"
					>
						{group.label}
					</Sidebar.GroupLabel>
					<Sidebar.GroupContent>
						<Sidebar.Menu>
							{#each group.items as item}
								{@const active = isActive(item.href)}
								{@const IconComp = item.icon}
								<Sidebar.MenuItem>
									<Sidebar.MenuButton
										isActive={active}
										tooltipContent={item.label}
										class="data-active:bg-blue-500/10 data-active:text-blue-500 data-active:shadow-[inset_3px_0_0_oklch(0.623_0.214_259.815)]"
									>
										{#snippet child({ props })}
											<a href={item.href} {...props}>
												<IconComp />
												<span>{item.label}</span>
											</a>
										{/snippet}
									</Sidebar.MenuButton>
								</Sidebar.MenuItem>
							{/each}
						</Sidebar.Menu>
					</Sidebar.GroupContent>
				</Sidebar.Group>
			{/each}
		</Sidebar.Content>

		<Sidebar.Footer
			class="shrink-0 border-t px-2 py-2"
			style="border-color:var(--ds-border);background:color-mix(in srgb,var(--surface) 80%,transparent)"
		>
			<a
				href="/app"
				class="flex items-center gap-2 px-2 py-2 text-xs text-muted-foreground transition-colors group-data-[collapsible=icon]:justify-center hover:text-foreground"
			>
				<ArrowLeft class="h-4 w-4" />
				<span class="group-data-[collapsible=icon]:hidden">Back to App</span>
			</a>
			<div class="flex items-center gap-1 px-1">
				<div class="flex flex-1 flex-col truncate px-1 group-data-[collapsible=icon]:hidden">
					<span class="truncate text-sm font-medium" style="color:var(--text-main)"
						>{data.user.name || data.user.email}</span
					>
					<span class="truncate text-[10px] text-muted-foreground">{data.user.email}</span>
				</div>
				<ModeToggle />
				<Button
					onclick={logout}
					variant="ghost"
					size="icon"
					class="h-8 w-8 text-muted-foreground hover:text-red-500"
				>
					<LogOut class="h-4 w-4" />
				</Button>
			</div>
		</Sidebar.Footer>

		<Sidebar.Rail />
	</Sidebar.Root>

	<Sidebar.Inset class="flex min-w-0 flex-col overflow-hidden bg-transparent">
		{#if !currentNav.hideHeader}
			<header
				class="flex h-14 shrink-0 items-center justify-between border-b px-2 backdrop-blur-md"
				style="border-color:var(--ds-border);background:color-mix(in srgb,var(--surface) 100%,transparent)"
			>
				<div class="flex items-center gap-3">
					<Sidebar.Trigger class="-ml-1 text-muted-foreground" />
					<div class="hidden h-4 w-px sm:block" style="background:var(--ds-border)"></div>
					<h1
						class="font-display text-base font-semibold tracking-tight"
						style="color:var(--text-main)"
					>
						{currentNav.label}
					</h1>
					<div class="hidden h-4 w-px md:block" style="background:var(--ds-border)"></div>
					<p class="hidden text-xs text-muted-foreground md:block">{currentNav.description}</p>
				</div>
				<Button variant="ghost" size="icon" class="relative h-9 w-9 text-muted-foreground">
					<Bell class="h-4 w-4" />
					<span class="absolute top-2 right-2 h-1.5 w-1.5 rounded-full bg-amber-400"></span>
				</Button>
			</header>
		{/if}

		<div class="w-full flex-1 overflow-y-auto">
			{@render children()}
		</div>
	</Sidebar.Inset>
</Sidebar.Provider>
