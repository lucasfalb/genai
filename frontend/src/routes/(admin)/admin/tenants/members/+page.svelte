<script lang="ts">
	import { goto } from '$app/navigation';
	import type { SuperadminTenantResponse } from '$lib/api/types';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import * as Command from '$lib/components/ui/command/index.js';
	import Building2 from '@lucide/svelte/icons/building-2';
	import Check from '@lucide/svelte/icons/check';
	import ChevronsUpDown from '@lucide/svelte/icons/chevrons-up-down';

	let { data } = $props();

	let tenants = $state<SuperadminTenantResponse[]>(data.tenants);
	let tenantOpen = $state(false);
	let selectedTenantId = $state('');
	const selectedTenant = $derived(tenants.find((tenant) => tenant.id === selectedTenantId) ?? null);

	async function openMembers() {
		if (!selectedTenant) return;
		await goto(`/admin/tenants/${selectedTenant.id}/members`);
	}
</script>

<div class="flex min-h-[calc(100vh-4rem)] items-center justify-center p-6">
	<div class="w-full max-w-xl rounded-lg border p-6" style="border-color:var(--ds-border);background:var(--surface)">
		<div class="mb-6 flex items-center gap-3">
			<div class="flex size-9 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
				<Building2 class="size-4" />
			</div>
			<div>
				<h1 class="font-display text-lg font-semibold">Tenant Members</h1>
				<p class="text-xs text-muted-foreground">Select a tenant to manage its visible members.</p>
			</div>
		</div>

		<div class="flex flex-col gap-2">
			<label class="text-sm font-medium">Tenant</label>
			<Popover.Root bind:open={tenantOpen}>
				<Popover.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="outline"
							class="w-full justify-between"
							role="combobox"
							aria-expanded={tenantOpen}
						>
							<span class="truncate">{selectedTenant ? `${selectedTenant.name} - ${selectedTenant.slug}` : 'Select tenant...'}</span>
							<ChevronsUpDown class="opacity-50" />
						</Button>
					{/snippet}
				</Popover.Trigger>
				<Popover.Content class="w-[420px] p-0">
					<Command.Root>
						<Command.Input placeholder="Search tenant..." />
						<Command.List>
							<Command.Empty>No tenants found.</Command.Empty>
							<Command.Group>
								{#each tenants as tenant (tenant.id)}
									<Command.Item
										value={`${tenant.name} ${tenant.slug}`}
										onSelect={() => {
											selectedTenantId = tenant.id;
											tenantOpen = false;
										}}
									>
										<Check class={selectedTenantId === tenant.id ? 'size-4' : 'size-4 text-transparent'} />
										<div class="min-w-0">
											<p class="truncate text-sm font-medium">{tenant.name}</p>
											<p class="truncate font-mono text-xs text-muted-foreground">{tenant.slug}</p>
										</div>
									</Command.Item>
								{/each}
							</Command.Group>
						</Command.List>
					</Command.Root>
				</Popover.Content>
			</Popover.Root>
		</div>

		<div class="mt-6 flex justify-end">
			<Button disabled={!selectedTenant} onclick={openMembers}>Open Members</Button>
		</div>
	</div>
</div>
