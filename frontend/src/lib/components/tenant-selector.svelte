<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import ChevronsUpDown from '@lucide/svelte/icons/chevrons-up-down';
	import Building2 from '@lucide/svelte/icons/building-2';
	import type { TenantAccessResponse } from '$lib/api/types';
	import { tenantStore } from '$lib/stores/tenant.svelte';
	import { tenantPath } from '$lib/routes/tenant';
	import { goto } from '$app/navigation';

	let {
		memberships,
		activeTenant
	}: {
		memberships: TenantAccessResponse[];
		activeTenant: TenantAccessResponse;
	} = $props();

	let tenantSearch = $state('');

	const filtered = $derived(
		memberships.filter((tenant) =>
			tenant.tenant_name.toLowerCase().includes(tenantSearch.toLowerCase())
		)
	);

	async function selectTenant(tenant: TenantAccessResponse) {
		tenantStore.setActiveTenant(tenant);
		await goto(tenantPath(tenant, '/dashboard'), { invalidateAll: true });
	}
</script>

<Sidebar.Menu>
	<Sidebar.MenuItem>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Sidebar.MenuButton
						{...props}
						size="lg"
						class="w-full group-data-[collapsible=icon]:min-w-[47px] data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
					>
						<!-- Icon box: gradient matches original dashboard style -->
						<div
							class="flex aspect-square size-8 shrink-0 items-center justify-center bg-gradient-to-tr from-blue-500/20 to-sky-400/20 text-blue-600 group-data-[collapsible=icon]:min-w-[47px] dark:text-blue-300"
							style="border:1px solid oklch(0.623 0.214 259.815 / 0.30)"
						>
							<Building2 class="size-4" />
						</div>
						<div class="grid flex-1 text-start leading-tight">
							<span class="truncate text-xs font-medium">{activeTenant.tenant_name}</span>
							<span class="truncate text-[10px] text-muted-foreground">{activeTenant.role}</span>
						</div>
						<ChevronsUpDown class="ms-auto size-3.5 shrink-0 text-muted-foreground" />
					</Sidebar.MenuButton>
				{/snippet}
			</DropdownMenu.Trigger>

			<DropdownMenu.Content class="w-56 min-w-56" align="start" side="right" sideOffset={4}>
				<!-- Search -->
				<div class="px-2 py-1.5">
					<input
						bind:value={tenantSearch}
						placeholder="Filter tenants..."
						class="w-full rounded-sm px-2 py-1 text-xs outline-none"
						style="background:var(--surface-hover);border:1px solid var(--ds-border);color:var(--text-main)"
					/>
				</div>

				{#each filtered as tenant (tenant.tenant_id)}
					<DropdownMenu.Item onSelect={() => selectTenant(tenant)} class="gap-2 p-2">
						<div
							class="flex size-6 items-center justify-center bg-gradient-to-tr from-blue-500/15 to-sky-400/15 text-blue-600 dark:text-blue-300"
							style="border:1px solid oklch(0.623 0.214 259.815 / 0.20)"
						>
							<Building2 class="size-3.5 shrink-0" />
						</div>
						<span class="flex-1 text-xs">{tenant.tenant_name}</span>
						<span class="text-[10px] text-muted-foreground">{tenant.role}</span>
						{#if tenant.tenant_id === activeTenant.tenant_id}
							<span class="size-1.5 rounded-full bg-blue-500"></span>
						{/if}
					</DropdownMenu.Item>
				{/each}

				{#if filtered.length === 0}
					<p class="px-3 py-2 text-xs text-muted-foreground">No tenants match.</p>
				{/if}
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</Sidebar.MenuItem>
</Sidebar.Menu>
