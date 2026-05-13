<script lang="ts">
	import { tick } from 'svelte';
	import type { DateValue } from '@internationalized/date';
	import type {
		SuperadminAuditLogResponse,
		AgentInstanceResponse,
		CollectionResponse,
		DocumentResponse
	} from '$lib/api/types';
	import { api, getErrorMessage } from '$lib/api/client';
	import * as Table from '$lib/components/ui/table/index.js';
	import * as Command from '$lib/components/ui/command/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import RangeCalendar from '$lib/components/ui/range-calendar/range-calendar.svelte';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { cn } from '$lib/utils.js';
	import Search from '@lucide/svelte/icons/search';
	import User from '@lucide/svelte/icons/user';
	import Shield from '@lucide/svelte/icons/shield';
	import Box from '@lucide/svelte/icons/box';
	import CalendarIcon from '@lucide/svelte/icons/calendar';
	import X from '@lucide/svelte/icons/x';
	import Check from '@lucide/svelte/icons/check';
	import ChevronsUpDown from '@lucide/svelte/icons/chevrons-up-down';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import { toast } from 'svelte-sonner';

	let { data } = $props();
	let logs = $state<SuperadminAuditLogResponse[]>(data.logs);
	let allActions = $state<string[]>(
		[...new Set(data.logs.map((l: SuperadminAuditLogResponse) => l.action))].sort()
	);
	let allResources = $state<string[]>(
		[...new Set(data.logs.map((l: SuperadminAuditLogResponse) => l.resource))].sort()
	);
	let instances = $state<AgentInstanceResponse[]>(data.instances);
	let collections = $state<CollectionResponse[]>(data.collections);
	let documents = $state<DocumentResponse[]>(data.documents);
	let loading = $state(false);
	let filterReloadTimer: ReturnType<typeof setTimeout> | undefined;
	let lastResolvedQueryKey = $state('');
	let inFlightQueryKey: string | null = null;
	let requestSequence = 0;

	let searchQuery = $state('');
	let actionFilter = $state('all');
	let resourceFilter = $state('all');
	let actionOpen = $state(false);
	let resourceOpen = $state(false);
	let dateRangeOpen = $state(false);
	let actionTriggerRef = $state<HTMLButtonElement>(null!);
	let resourceTriggerRef = $state<HTMLButtonElement>(null!);

	let dateRange = $state<{ start: DateValue | undefined; end: DateValue | undefined } | undefined>(
		undefined
	);
	lastResolvedQueryKey = queryKey(buildAuditQuery());

	const instanceNames = $derived(new Map(instances.map((i) => [i.id, i.name])));
	const collectionNames = $derived(new Map(collections.map((c) => [c.id, c.name])));
	const documentNames = $derived(new Map(documents.map((d) => [d.id, d.filename])));

	const uniqueActions = $derived(allActions);
	const uniqueResources = $derived(allResources);

	const filteredLogs = $derived.by(() => {
		const q = searchQuery.toLowerCase().trim();
		return logs.filter((l) => {
			if (actionFilter !== 'all' && l.action !== actionFilter) return false;
			if (resourceFilter !== 'all' && l.resource !== resourceFilter) return false;
			if (!q) return true;
			return (
				l.action.toLowerCase().includes(q) ||
				l.resource.toLowerCase().includes(q) ||
				(l.resource_id ?? '').toLowerCase().includes(q) ||
				(l.user_email ?? '').toLowerCase().includes(q) ||
				(l.user_name ?? '').toLowerCase().includes(q) ||
				resolveResourceName(l.resource, l.resource_id).toLowerCase().includes(q)
			);
		});
	});
	const isRefetching = $derived(loading && filteredLogs.length > 0);
	const hasPendingServerFilter = $derived(queryKey(buildAuditQuery()) !== lastResolvedQueryKey || loading);
	const isLoadingFilteredLogs = $derived(hasPendingServerFilter && filteredLogs.length === 0);
	const hasActiveFilters = $derived(
		actionFilter !== 'all' ||
			resourceFilter !== 'all' ||
			dateRange !== undefined ||
			searchQuery.trim() !== ''
	);
	const filterKey = $derived(
		[
			actionFilter,
			resourceFilter,
			dateRange?.start?.toString() ?? '',
			dateRange?.end?.toString() ?? ''
		].join('|')
	);
	const dateRangeLabel = $derived(
		dateRange?.start && dateRange?.end
			? `${dateRange.start.toDate('utc').toLocaleDateString('pt-BR')} - ${dateRange.end.toDate('utc').toLocaleDateString('pt-BR')}`
			: dateRange?.start
				? `${dateRange.start.toDate('utc').toLocaleDateString('pt-BR')} - ...`
				: 'Date range'
	);

	$effect(() => {
		filterKey;
		if (filterReloadTimer) clearTimeout(filterReloadTimer);
		filterReloadTimer = setTimeout(() => {
			void loadLogs();
		}, 350);
		return () => {
			if (filterReloadTimer) clearTimeout(filterReloadTimer);
		};
	});

	function closeAndFocus(ref: HTMLButtonElement | undefined) {
		tick().then(() => ref?.focus());
	}

	function resolveResourceName(resource: string, resourceId: string | null): string {
		if (!resourceId) return '—';
		if (resource === 'agent_instances') return instanceNames.get(resourceId) ?? resourceId;
		if (resource === 'collections') return collectionNames.get(resourceId) ?? resourceId;
		if (resource === 'documents') return documentNames.get(resourceId) ?? resourceId;
		return resourceId;
	}

	function resolveUserLabel(log: SuperadminAuditLogResponse): string {
		if (log.user_email) return log.user_email;
		if (log.user_name) return log.user_name;
		return log.actor_role || log.actor_type;
	}

	function buildAuditQuery(): Record<string, string> {
		const params: Record<string, string> = { limit: '100' };
		if (actionFilter !== 'all') params.action = actionFilter;
		if (resourceFilter !== 'all') params.resource = resourceFilter;
		if (dateRange?.start) {
			const d = dateRange.start.toDate('utc');
			d.setUTCHours(0, 0, 0, 0);
			params.started_at = d.toISOString();
		}
		if (dateRange?.end) {
			const d = dateRange.end.toDate('utc');
			d.setUTCHours(23, 59, 59, 999);
			params.ended_at = d.toISOString();
		}
		return params;
	}

	async function loadLogs(options: { force?: boolean } = {}) {
		const query = buildAuditQuery();
		const key = queryKey(query);
		if (!options.force && key === lastResolvedQueryKey) return;
		if (key === inFlightQueryKey) return;

		const requestId = ++requestSequence;
		inFlightQueryKey = key;
		loading = true;
		try {
			const nextLogs = await api.get<SuperadminAuditLogResponse[]>('/tenant/audit', query);
			if (requestId !== requestSequence) return;
			logs = nextLogs;
			for (const log of nextLogs) {
				if (!allActions.includes(log.action)) allActions = [...allActions, log.action].sort();
				if (!allResources.includes(log.resource))
					allResources = [...allResources, log.resource].sort();
			}
			lastResolvedQueryKey = key;
		} catch (err) {
			if (requestId !== requestSequence) return;
			toast.error(getErrorMessage(err, 'Nao foi possivel carregar os logs de auditoria.'));
		} finally {
			if (requestId === requestSequence) {
				loading = false;
				inFlightQueryKey = null;
			}
		}
	}

	function applyFilters() {
		void loadLogs({ force: true });
	}

	function clearFilters() {
		const hadFilters = hasActiveFilters;
		searchQuery = '';
		actionFilter = 'all';
		resourceFilter = 'all';
		dateRange = undefined;
		if (!hadFilters) void loadLogs({ force: true });
	}

	function applyFilterOnEnter(event: KeyboardEvent) {
		if (event.key === 'Enter') applyFilters();
	}

	function formatDate(value: string): string {
		return new Date(value).toLocaleString('pt-BR');
	}

	function getActionColor(action: string): string {
		if (action.includes('created') || action.includes('added')) return 'text-emerald-500';
		if (action.includes('deleted') || action.includes('removed')) return 'text-red-500';
		if (action.includes('updated') || action.includes('changed') || action.includes('toggled'))
			return 'text-blue-500';
		return 'text-muted-foreground';
	}

	function queryKey(params: Record<string, string>) {
		const query = new URLSearchParams(params);
		query.sort();
		return query.toString();
	}
</script>

<div class="flex flex-col gap-4 p-4">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div class="flex max-w-4xl min-w-[300px] flex-1 flex-wrap items-center gap-2">
			<div class="relative w-full max-w-xs">
				<Search class="absolute top-2.5 left-2.5 h-4 w-4 text-muted-foreground" />
				<Input
					placeholder="Search logs..."
					bind:value={searchQuery}
					class="h-9 bg-background pl-9"
					onkeydown={applyFilterOnEnter}
				/>
			</div>

			<Popover.Root bind:open={actionOpen}>
				<Popover.Trigger bind:ref={actionTriggerRef}>
					{#snippet child({ props })}
						<Button
							variant="outline"
							class="h-9 w-[240px] justify-between bg-background"
							{...props}
							role="combobox"
							aria-expanded={actionOpen}
						>
							<span class="truncate">{actionFilter === 'all' ? 'All Actions' : actionFilter}</span>
							<ChevronsUpDown class="ms-2 size-4 shrink-0 opacity-50" />
						</Button>
					{/snippet}
				</Popover.Trigger>
				<Popover.Content class="w-[240px] p-0">
					<Command.Root>
						<Command.Input placeholder="Search action..." />
						<Command.List>
							<Command.Empty>No actions found.</Command.Empty>
							<Command.Group>
								<Command.Item
									value="__all__"
									onSelect={() => {
										actionFilter = 'all';
										actionOpen = false;
										closeAndFocus(actionTriggerRef);
										applyFilters();
									}}
								>
									<Check class={cn('size-4', actionFilter !== 'all' && 'text-transparent')} />
									All Actions
								</Command.Item>
								{#each uniqueActions as act}
									<Command.Item
										value={act}
										onSelect={() => {
											actionFilter = act;
											actionOpen = false;
											closeAndFocus(actionTriggerRef);
											applyFilters();
										}}
									>
										<Check class={cn('size-4', actionFilter !== act && 'text-transparent')} />
										{act}
									</Command.Item>
								{/each}
							</Command.Group>
						</Command.List>
					</Command.Root>
				</Popover.Content>
			</Popover.Root>

			<Popover.Root bind:open={resourceOpen}>
				<Popover.Trigger bind:ref={resourceTriggerRef}>
					{#snippet child({ props })}
						<Button
							variant="outline"
							class="h-9 w-[240px] justify-between bg-background"
							{...props}
							role="combobox"
							aria-expanded={resourceOpen}
						>
							<span class="truncate"
								>{resourceFilter === 'all' ? 'All Resources' : resourceFilter}</span
							>
							<ChevronsUpDown class="ms-2 size-4 shrink-0 opacity-50" />
						</Button>
					{/snippet}
				</Popover.Trigger>
				<Popover.Content class="w-[240px] p-0">
					<Command.Root>
						<Command.Input placeholder="Search resource..." />
						<Command.List>
							<Command.Empty>No resources found.</Command.Empty>
							<Command.Group>
								<Command.Item
									value="__all__"
									onSelect={() => {
										resourceFilter = 'all';
										resourceOpen = false;
										closeAndFocus(resourceTriggerRef);
										applyFilters();
									}}
								>
									<Check class={cn('size-4', resourceFilter !== 'all' && 'text-transparent')} />
									All Resources
								</Command.Item>
								{#each uniqueResources as res}
									<Command.Item
										value={res}
										onSelect={() => {
											resourceFilter = res;
											resourceOpen = false;
											closeAndFocus(resourceTriggerRef);
											applyFilters();
										}}
									>
										<Check class={cn('size-4', resourceFilter !== res && 'text-transparent')} />
										{res}
									</Command.Item>
								{/each}
							</Command.Group>
						</Command.List>
					</Command.Root>
				</Popover.Content>
			</Popover.Root>

			<Popover.Root bind:open={dateRangeOpen}>
				<Popover.Trigger>
					{#snippet child({ props })}
						<Button variant="outline" class="h-9 gap-2 bg-background" {...props}>
							<CalendarIcon class="size-4" />
							<span class="text-xs">{dateRangeLabel}</span>
						</Button>
					{/snippet}
				</Popover.Trigger>
				<Popover.Content class="w-auto p-0" align="start">
					<RangeCalendar bind:value={dateRange} numberOfMonths={2} locale="pt-BR" />
					<div class="border-t p-2" style="border-color:var(--ds-border)">
						<Button
							class="w-full"
							size="sm"
							onclick={() => {
								dateRangeOpen = false;
								applyFilters();
							}}
						>
							Apply range
						</Button>
					</div>
				</Popover.Content>
			</Popover.Root>

			{#if hasActiveFilters}
				<Button
					variant="ghost"
					size="sm"
					class="h-9 gap-1 border bg-background text-muted-foreground hover:bg-muted"
					onclick={clearFilters}
				>
					<X class="size-4" />
					Clear
				</Button>
			{/if}
		</div>
	</div>

	<div class="relative overflow-hidden border bg-card">
		{#if isRefetching}
			<div
				class="pointer-events-none absolute top-3 right-3 z-10 flex items-center gap-2 border bg-background/90 px-2.5 py-1.5 text-xs text-muted-foreground backdrop-blur"
			>
				<RefreshCw class="size-3 animate-spin" />
				Updating
			</div>
		{/if}
		<Table.Root
			containerClass="scrollbar-none max-h-[600px] overflow-auto bg-card"
			class="w-full table-fixed"
		>
			<Table.Header class="sticky top-0 z-10 bg-background">
				<Table.Row class="bg-background hover:bg-background">
					<Table.Head
						class="w-[180px] bg-background py-2 text-[11px] font-bold tracking-wider uppercase"
						>Date</Table.Head
					>
					<Table.Head
						class="w-[200px] bg-background py-2 text-[11px] font-bold tracking-wider uppercase"
						>Actor</Table.Head
					>
					<Table.Head class="bg-background py-2 text-[11px] font-bold tracking-wider uppercase"
						>Action</Table.Head
					>
					<Table.Head
						class="w-[200px] bg-background py-2 text-[11px] font-bold tracking-wider uppercase"
						>Resource</Table.Head
					>
					<Table.Head
						class="w-[120px] bg-background py-2 text-right text-[11px] font-bold tracking-wider uppercase"
						>Details</Table.Head
					>
				</Table.Row>
			</Table.Header>

			<Table.Body>
				{#if isLoadingFilteredLogs}
					<Table.Row class="bg-card hover:bg-card">
						<Table.Cell colspan={5} class="h-32 text-center text-muted-foreground">
							<div class="flex flex-col items-center gap-2">
								<RefreshCw class="size-4 animate-spin" />
								<span class="text-sm font-medium text-foreground">Loading logs</span>
							</div>
						</Table.Cell>
					</Table.Row>
				{:else if filteredLogs.length === 0}
					<Table.Row class="bg-card hover:bg-card">
						<Table.Cell colspan={5} class="h-32 text-center text-muted-foreground">
							<div class="flex flex-col items-center gap-1">
								<span class="text-sm font-medium text-foreground">No logs found</span>
								<span class="text-xs">Try adjusting your search or filter criteria.</span>
							</div>
						</Table.Cell>
					</Table.Row>
				{:else}
					{#each filteredLogs as log (log.id)}
						<Table.Row class="group bg-card transition-colors hover:bg-muted/30">
							<Table.Cell class="py-3 font-mono text-[10px] text-muted-foreground">
								{formatDate(log.created_at)}
							</Table.Cell>

							<Table.Cell class="py-3">
								<div class="flex items-center gap-2">
									{#if log.actor_type === 'superadmin'}
										<Shield class="h-3 w-3 shrink-0 text-purple-400" />
									{:else}
										<User class="h-3 w-3 shrink-0 text-blue-400" />
									{/if}
									<div class="min-w-0">
										<span class="block truncate text-[11px] font-medium"
											>{resolveUserLabel(log)}</span
										>
										{#if log.user_email && log.actor_role}
											<span class="block truncate font-mono text-[9px] text-muted-foreground"
												>{log.actor_role}</span
											>
										{/if}
									</div>
								</div>
							</Table.Cell>

							<Table.Cell class="py-3">
								<span class="text-xs font-semibold {getActionColor(log.action)}">
									{log.action}
								</span>
							</Table.Cell>

							<Table.Cell class="py-3">
								<div class="flex items-center gap-2 overflow-hidden">
									<Box class="h-3 w-3 shrink-0 text-muted-foreground" />
									<div class="flex min-w-0 flex-col">
										<span class="truncate text-[11px] font-medium">{log.resource}</span>
										<span
											class="truncate font-mono text-[9px] text-muted-foreground"
											title={log.resource_id ?? ''}
										>
											{resolveResourceName(log.resource, log.resource_id)}
										</span>
									</div>
								</div>
							</Table.Cell>

							<Table.Cell class="py-3 text-right">
								<Badge
									variant="outline"
									class="h-5 px-1.5 text-[9px] font-bold tracking-tighter uppercase"
								>
									Audit
								</Badge>
							</Table.Cell>
						</Table.Row>
					{/each}
				{/if}
			</Table.Body>
		</Table.Root>
		<div class="border-t bg-card px-4 py-2">
			<p class="text-[10px] font-bold tracking-widest text-muted-foreground uppercase">
				Showing {filteredLogs.length} of {logs.length} entries
			</p>
		</div>
	</div>
</div>

<style>
	:global(td) {
		white-space: nowrap;
	}
</style>
