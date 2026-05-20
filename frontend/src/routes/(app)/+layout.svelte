<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import ModeToggle from '$lib/components/mode-toggle.svelte';
	import TenantSelector from '$lib/components/tenant-selector.svelte';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import * as Command from '$lib/components/ui/command/index.js';

	import Bot from '@lucide/svelte/icons/bot';
	import Plus from '@lucide/svelte/icons/plus';
	import Network from '@lucide/svelte/icons/network';
	import Cpu from '@lucide/svelte/icons/cpu';
	import Activity from '@lucide/svelte/icons/activity';
	import Library from '@lucide/svelte/icons/library';
	import Settings from '@lucide/svelte/icons/settings';
	import Users from '@lucide/svelte/icons/users';
	import LogOut from '@lucide/svelte/icons/log-out';
	import Bell from '@lucide/svelte/icons/bell';
	import Search from '@lucide/svelte/icons/search';
	import History from '@lucide/svelte/icons/history';
import MessagesSquare from '@lucide/svelte/icons/messages-square';
	import type { Component } from 'svelte';
	import { goto } from '$app/navigation';
	import { authApi } from '$lib/api/auth';
	import { authStore } from '$lib/stores/auth.svelte';
	import { tenantStore } from '$lib/stores/tenant.svelte';
	import { startProactiveRefresh, stopProactiveRefresh } from '$lib/api/client';
	import { tenantPath } from '$lib/routes/tenant';
	import { toast } from 'svelte-sonner';

	let { data, children } = $props();
	let commandOpen = $state(false);
	let isMac = $state(false);
	const appBase = $derived(tenantPath(data.activeTenant));
	const platformName = $derived(data.publicSettings?.platform_name || 'GENAI');

	$effect(() => {
		authStore.user = data.user;
		authStore.memberships = data.memberships;
		if (data.activeTenant) {
			tenantStore.setActiveTenant(data.activeTenant);
		}
	});

	onMount(() => {
		if (data.refreshToken) {
			authStore.setTokens(data.accessToken, data.refreshToken);
			startProactiveRefresh();
		}
		return () => stopProactiveRefresh();
	});

	$effect(() => {
		isMac = /Mac|iPhone|iPad|iPod/.test(navigator.platform);
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
			label: 'Workspace',
			items: [
				{ href: '/instances', label: 'Agents', icon: Network, description: 'Manage tenant agents' },
				{
					href: '/collections',
					label: 'Collections & Knowledge',
					icon: Library,
					description: 'RAG collections and knowledge bases'
				},
				{
					href: '/observability',
					label: 'Observability',
					icon: Activity,
					description: 'Logs, traces and execution health'
				},
				{
					href: '/sessions',
					label: 'Sessions',
					icon: MessagesSquare,
					description: 'Chat session history and transcripts'
				},
				{
					href: '/logs',
					label: 'Audit Logs',
					icon: History,
					description: 'Track tenant changes and activity'
				},
				{
					href: '/settings',
					label: 'Configuration',
					icon: Settings,
					description: 'Tenant AI and credentials settings'
				},
				{
					href: '/settings/members',
					label: 'Members',
					icon: Users,
					description: 'Members, roles and invitations'
				}
			]
		}
	];

	const allNavItems = navGroups.flatMap((g) => g.items);

	const appPath = $derived(
		page.url.pathname.startsWith(appBase)
			? page.url.pathname.slice(appBase.length) || '/dashboard'
			: page.url.pathname
	);
	const currentNav = $derived(
		[...allNavItems]
			.sort((a, b) => b.href.length - a.href.length)
			.find(
				(item) =>
					appPath === item.href || (item.href !== '/dashboard' && appPath.startsWith(`${item.href}/`))
			) ?? allNavItems[0]
	);

	function handleKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
			e.preventDefault();
			commandOpen = !commandOpen;
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
			tenantStore.clearTenant();
			await goto('/login');
		}
	}
</script>

<svelte:head>
	<title>{platformName}</title>
</svelte:head>

<svelte:window onkeydown={handleKeydown} />

<!-- Ambient glows -->
<div
	class="pointer-events-none fixed top-[-20%] left-[-10%] h-[600px] w-[600px] rounded-full bg-blue-600/10 blur-[150px]"
	style="z-index:0"
></div>
<div
	class="pointer-events-none fixed right-[-5%] bottom-[-10%] h-[500px] w-[500px] rounded-full bg-cyan-600/5 blur-[120px]"
	style="z-index:0"
></div>
<div
	class="pointer-events-none fixed top-[20%] right-[15%] h-[300px] w-[300px] rounded-full bg-sky-500/10 blur-[100px]"
	style="z-index:0"
></div>

<!-- Command palette -->
<Command.Dialog bind:open={commandOpen} title="Search" description="Search pages and actions">
	<Command.Input placeholder="Search pages, instances, agents..." />
	<Command.List>
		<Command.Empty>No results found.</Command.Empty>
		<Command.Group heading="Navigation">
			{#each allNavItems as item}
				{@const IconComp = item.icon}
				<Command.LinkItem
					href={`${appBase}${item.href}`}
					onSelect={() => (commandOpen = false)}
					class="flex items-center gap-2"
				>
					<IconComp />
					<div class="flex flex-col">
						<span>{item.label}</span>
						<span class="text-xs text-muted-foreground">{item.description}</span>
					</div>
					<Command.Shortcut>↵</Command.Shortcut>
				</Command.LinkItem>
			{/each}
		</Command.Group>
		<Command.Separator />
		<Command.Group heading="Quick Actions">
			<Command.Item onSelect={() => (commandOpen = false)}>
				<Plus />
				<span>New Agent</span>
				<Command.Shortcut>↵</Command.Shortcut>
			</Command.Item>
		</Command.Group>
	</Command.List>
</Command.Dialog>

<Sidebar.Provider
	class="h-screen overflow-hidden selection:bg-blue-500/30"
	style="position:relative;z-index:1"
>
	<Sidebar.Root
		collapsible="icon"
		class="glass-panel border-r"
		style="border-color:var(--ds-border)"
	>
		<!-- Logo -->
		<Sidebar.Header
			class="h-14 shrink-0 flex-row items-center gap-2 border-b px-4"
			style="border-color:var(--ds-border)"
		>
			<Bot class="size-5 shrink-0 text-blue-500" />
			<span
				class="font-display text-lg font-semibold tracking-tight group-data-[collapsible=icon]:hidden"
				style="color:var(--text-main)">{platformName}</span
			>
		</Sidebar.Header>

		<!-- Tenant selector -->
		<Sidebar.Header class="shrink-0 border-b" style="border-color:var(--ds-border)">
			<TenantSelector memberships={data.memberships} activeTenant={data.activeTenant} />
		</Sidebar.Header>

		<!-- Navigation -->
		<Sidebar.Content class="mt-1">
			{#each navGroups as group, gi}
				{#if gi > 0}<Sidebar.Separator />{/if}
				<Sidebar.Group>
					<Sidebar.GroupLabel
						class="font-display text-[10px] font-semibold tracking-widest uppercase"
					>
						{group.label}
					</Sidebar.GroupLabel>
					<Sidebar.GroupContent>
						<Sidebar.Menu>
							{#each group.items as item}
								{@const isActive = currentNav.href === item.href}
								{@const IconComp = item.icon}
								<Sidebar.MenuItem>
									<Sidebar.MenuButton
										{isActive}
										tooltipContent={item.label}
										class="data-active:bg-blue-500/10 data-active:text-blue-500 data-active:shadow-[inset_3px_0_0_oklch(0.623_0.214_259.815)]"
									>
										{#snippet child({ props })}
											<a href={`${appBase}${item.href}`} {...props}>
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

		<!-- User footer -->
		<Sidebar.Footer
			class="shrink-0 border-t px-2 py-2"
			style="border-color:var(--ds-border);background:color-mix(in srgb,var(--surface) 80%,transparent)"
		>
			<div class="flex items-center gap-1">
				<button
					class="flex flex-1 items-center gap-2.5 overflow-hidden px-2 py-1.5 transition-colors group-data-[collapsible=icon]:w-full group-data-[collapsible=icon]:flex-none group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-1 hover:bg-sidebar-accent"
				>
					<div
						class="flex h-8 w-8 shrink-0 items-center justify-center bg-gradient-to-br from-slate-700 to-slate-900 text-xs font-bold text-white"
						style="border:1px solid var(--ds-border-hover)"
					>
						LA
					</div>
					<div
						class="flex flex-1 flex-col truncate text-left leading-tight group-data-[collapsible=icon]:hidden"
					>
						<span class="truncate text-sm font-medium" style="color:var(--text-main)"
							>{data.user.name || data.user.email}</span
						>
						<span class="truncate text-[10px] text-muted-foreground">{data.user.email}</span>
					</div>
				</button>
				<div class="flex items-center gap-0.5 group-data-[collapsible=icon]:hidden">
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
			</div>
		</Sidebar.Footer>

		<Sidebar.Rail />
	</Sidebar.Root>

	<!-- Main content -->
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
					{#if currentNav.description}
						<div class="hidden h-4 w-px md:block" style="background:var(--ds-border)"></div>
						<p class="hidden text-xs text-muted-foreground md:block">{currentNav.description}</p>
					{/if}
				</div>
				<div class="flex items-center gap-2">
					<button
						onclick={() => (commandOpen = true)}
						class="ds-input relative hidden h-10 w-54 cursor-pointer items-center gap-2 py-2 pr-3 pl-9 text-left text-sm transition-colors lg:flex"
					>
						<Search
							class="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-muted-foreground"
						/>
						<span class="flex-1 text-xs text-muted-foreground/60">Search in GENAI...</span>
						<kbd
							class="inline-flex items-center gap-0.5 rounded-sm px-2 py-0.5 font-mono text-[10px] leading-none"
							style="border:1px solid var(--ds-border-hover);background:var(--surface-hover);color:var(--text-muted)"
							>{isMac ? '⌘' : 'Ctrl'}&thinsp;K</kbd
						>
					</button>
				</div>
			</header>
		{/if}

		<div class="w-full flex-1 overflow-y-auto">
			{@render children()}
		</div>
	</Sidebar.Inset>
</Sidebar.Provider>
