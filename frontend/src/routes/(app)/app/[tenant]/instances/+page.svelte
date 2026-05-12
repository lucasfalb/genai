<script lang="ts">
	import Bot from '@lucide/svelte/icons/bot';
	import Plus from '@lucide/svelte/icons/plus';
	import Search from '@lucide/svelte/icons/search';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';

	import * as Table from '$lib/components/ui/table';
	import * as Select from '$lib/components/ui/select';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Input } from '$lib/components/ui/input';

	import { page } from '$app/state';
	import { tenantBaseFromPath } from '$lib/routes/tenant';

	let { data } = $props();
	const instances = $derived(data.instances);
	const appBase = $derived(tenantBaseFromPath(page.url.pathname));

	// Estados de Filtro
	let searchQuery = $state('');
	let statusFilter = $state('all');

	const statusOptions = [
		{ value: 'all', label: 'All Status' },
		{ value: 'active', label: 'Active' },
		{ value: 'inactive', label: 'Inactive' },
		{ value: 'draft', label: 'Draft' }
	];

	// Lógica de filtragem reativa
	const filteredInstances = $derived(
		instances.filter((inst) => {
			const matchesSearch = inst.name.toLowerCase().includes(searchQuery.toLowerCase());
			const matchesStatus = statusFilter === 'all' || inst.status === statusFilter;
			return matchesSearch && matchesStatus;
		})
	);

	const STATUS_VARIANT: Record<string, 'default' | 'secondary' | 'outline'> = {
		active: 'default',
		inactive: 'secondary',
		draft: 'outline'
	};
</script>

<div class="flex flex-col gap-4 p-4">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div class="flex max-w-2xl min-w-[300px] flex-1 items-center gap-2">
			<div class="relative w-full max-w-xs">
				<Search class="absolute top-2.5 left-2.5 h-4 w-4 text-muted-foreground" />
				<Input placeholder="Search agents..." bind:value={searchQuery} class="h-9 pl-9" />
			</div>

			<Select.Root type="single" bind:value={statusFilter}>
				<Select.Trigger class="min-h-9 w-[140px] bg-card">
					{statusOptions.find((o) => o.value === statusFilter)?.label}
				</Select.Trigger>
				<Select.Content>
					{#each statusOptions as option}
						<Select.Item value={option.value}>{option.label}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		</div>

		<Button href="{appBase}/instances/new" size="sm" class="h-9 gap-2 shadow-sm">
			<Plus class="h-4 w-4" />
			New Agent
		</Button>
	</div>

	<div class="overflow-hidden rounded-none border bg-card shadow-sm">
		<Table.Root class="w-full table-fixed">
			<Table.Header class="bg-muted/40">
				<Table.Row class="hover:bg-transparent">
					<Table.Head class="w-[40%] py-2 text-[11px] font-bold tracking-wider uppercase"
						>Agent</Table.Head
					>
					<Table.Head
						class="hidden py-2 text-[11px] font-bold tracking-wider uppercase md:table-cell"
						>Configuration</Table.Head
					>
					<Table.Head class="w-[120px] py-2 text-[11px] font-bold tracking-wider uppercase"
						>Status</Table.Head
					>
					<Table.Head class="w-[50px] py-2"></Table.Head>
				</Table.Row>
			</Table.Header>

			<Table.Body>
				{#if filteredInstances.length === 0}
					<Table.Row>
						<Table.Cell colspan={4} class="h-32 text-center text-muted-foreground">
							<div class="flex flex-col items-center gap-1">
								<span class="text-sm font-medium text-foreground">No agents found</span>
								<span class="text-xs">Try adjusting your filters or search query.</span>
							</div>
						</Table.Cell>
					</Table.Row>
				{:else}
					{#each filteredInstances as inst (inst.id)}
						<Table.Row class="group transition-colors hover:bg-muted/30">
							<Table.Cell class="py-3">
								<a
									href="{appBase}/instances/{inst.id}"
									class="flex items-center gap-3 overflow-hidden"
								>
									<div
										class="flex h-8 w-8 shrink-0 items-center justify-center rounded border bg-background transition-all group-hover:border-primary/40"
									>
										<Bot class="h-4 w-4 text-muted-foreground group-hover:text-primary" />
									</div>
									<span class="truncate text-sm font-semibold">{inst.name}</span>
								</a>
							</Table.Cell>

							<Table.Cell class="hidden py-3 md:table-cell">
								<span class="block truncate text-xs text-muted-foreground">
									{inst.description || inst.model || '—'}
								</span>
							</Table.Cell>

							<Table.Cell class="py-3">
								<Badge
									variant={STATUS_VARIANT[inst.status] ?? 'secondary'}
									class="px-2 py-0 text-[10px] font-bold tracking-tight uppercase"
								>
									{inst.status}
								</Badge>
							</Table.Cell>

							<Table.Cell class="py-3 text-right">
								<Button
									variant="ghost"
									size="icon"
									href="{appBase}/instances/{inst.id}"
									class="h-7 w-7 text-muted-foreground/30 group-hover:text-foreground"
								>
									<ChevronRight class="h-4 w-4" />
								</Button>
							</Table.Cell>
						</Table.Row>
					{/each}
				{/if}
			</Table.Body>
		</Table.Root>

		<div class="border-t bg-muted/20 px-4 py-2">
			<p class="text-[10px] font-bold tracking-widest text-muted-foreground uppercase">
				Showing {filteredInstances.length} of {instances.length} agents
			</p>
		</div>
	</div>
</div>

<style>
	:global(td) {
		white-space: nowrap;
	}
</style>
