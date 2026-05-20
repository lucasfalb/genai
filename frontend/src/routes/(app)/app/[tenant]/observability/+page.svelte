<script lang="ts">
	import { replaceState } from '$app/navigation';
	import { page } from '$app/state';
	import BarChart3 from '@lucide/svelte/icons/bar-chart-3';
	import Bot from '@lucide/svelte/icons/bot';
	import CalendarIcon from '@lucide/svelte/icons/calendar';
	import Clock3 from '@lucide/svelte/icons/clock-3';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Search from '@lucide/svelte/icons/search';
	import X from '@lucide/svelte/icons/x';
	import Zap from '@lucide/svelte/icons/zap';
	import * as Sheet from '$lib/components/ui/sheet/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import RangeCalendar from '$lib/components/ui/range-calendar/range-calendar.svelte';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { toast } from 'svelte-sonner';
	import type { DateValue } from '@internationalized/date';
	import RunTracePanel from '$lib/components/instance/run-trace-panel.svelte';
	import { tracesApi, type TenantTraceListParams } from '$lib/api/chat';
	import { getErrorMessage } from '$lib/api/client';
	import type { AgentInstanceResponse, RunTraceListItem } from '$lib/api/types';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	type InstanceTokenSummary = {
		instance_id: string;
		name: string;
		runs: number;
		total_tokens: number;
		prompt_tokens: number;
		completion_tokens: number;
		embedding_tokens: number;
		duration_ms: number;
	};

	const PAGE_SIZE = 20;

	let runs = $state<RunTraceListItem[]>(data.runs);
	let instances = $state<AgentInstanceResponse[]>(data.instances);
	let loading = $state(false);
	let loadingMore = $state(false);
	let hasMore = $state(data.hasMore);
	let sheetOpen = $state(false);
	let selectedRun = $state<RunTraceListItem | null>(null);
	let resolvedRunDetailsId = $state<string | null>(null);
	let closingRunDetailsId = $state<string | null>(null);
	let sentinel = $state<HTMLDivElement | null>(null);

	let agentFilter = $state('all');
	let searchQuery = $state('');
	let dateRangeOpen = $state(false);
	let dateRange = $state<{ start: DateValue | undefined; end: DateValue | undefined } | undefined>(
		undefined
	);
	let filterReloadTimer: ReturnType<typeof setTimeout> | undefined;
	let lastResolvedQueryKey = queryKey(buildTraceQuery(PAGE_SIZE));
	let inFlightQueryKey: string | null = null;
	let requestSequence = 0;
	let loadMoreQueryKey: string | null = null;

	const instanceNames = $derived(
		new Map(instances.map((instance) => [instance.id, instance.name]))
	);

	const agentOptions = $derived([
		{ value: 'all', label: 'All Agents' },
		...instances.map((i) => ({ value: i.id, label: i.name }))
	]);

	const filteredRuns = $derived(runs);

	const runsWithTokens = $derived(filteredRuns.filter((run) => (run.total_tokens ?? 0) > 0));
	const totalRuns = $derived(filteredRuns.length);
	const llmTokens = $derived(sum(filteredRuns, 'total_tokens'));
	const embeddingTokens = $derived(sum(filteredRuns, 'embedding_tokens'));
	const totalTokens = $derived(llmTokens + embeddingTokens);
	const promptTokens = $derived(sum(filteredRuns, 'prompt_tokens'));
	const completionTokens = $derived(sum(filteredRuns, 'completion_tokens'));
	const averageTokens = $derived(totalRuns > 0 ? Math.round(totalTokens / totalRuns) : 0);
	const totalDuration = $derived(filteredRuns.reduce((acc, run) => acc + run.duration_ms, 0));
	const averageDuration = $derived(totalRuns > 0 ? Math.round(totalDuration / totalRuns) : 0);
	const maxRunTokens = $derived(Math.max(0, ...filteredRuns.map((run) => runTotalTokens(run))));
	const instanceSummaries = $derived(buildInstanceSummaries(filteredRuns, instanceNames));
	const isRefetching = $derived(loading && filteredRuns.length > 0);
	const dateRangeLabel = $derived(
		dateRange?.start && dateRange?.end
			? `${dateRange.start.toDate('utc').toLocaleDateString('pt-BR')} - ${dateRange.end.toDate('utc').toLocaleDateString('pt-BR')}`
			: dateRange?.start
				? `${dateRange.start.toDate('utc').toLocaleDateString('pt-BR')} - ...`
				: 'Date range'
	);

	const hasActiveFilters = $derived(
		agentFilter !== 'all' || searchQuery !== '' || dateRange !== undefined
	);
	const filterKey = $derived(
		[
			agentFilter,
			searchQuery.trim(),
			dateRange?.start?.toString() ?? '',
			dateRange?.end?.toString() ?? ''
		].join('|')
	);

	$effect(() => {
		filterKey;
		if (filterReloadTimer) clearTimeout(filterReloadTimer);
		filterReloadTimer = setTimeout(() => {
			void loadDashboard();
		}, 350);
		return () => {
			if (filterReloadTimer) clearTimeout(filterReloadTimer);
		};
	});

	$effect(() => {
		if (sentinel && hasMore && !loading && !loadingMore) {
			const observer = new IntersectionObserver(
				(entries) => {
					if (entries[0]?.isIntersecting && hasMore && !loadingMore) {
						void loadMore();
					}
				},
				{ rootMargin: '400px' }
			);
			observer.observe(sentinel);
			return () => observer.disconnect();
		}
	});

	$effect(() => {
		const runId = page.url.searchParams.get('runDetails');
		if (!runId) {
			resolvedRunDetailsId = null;
			closingRunDetailsId = null;
			selectedRun = null;
			sheetOpen = false;
			return;
		}
		if (runId === closingRunDetailsId && !sheetOpen) return;
		if (runId === resolvedRunDetailsId && sheetOpen) return;
		void openRunDetailsById(runId);
	});

	async function loadDashboard(options: { force?: boolean } = {}) {
		const query = buildTraceQuery(PAGE_SIZE);
		const key = queryKey(query);
		if (!options.force && key === lastResolvedQueryKey) return;
		if (key === inFlightQueryKey) return;

		const requestId = ++requestSequence;
		inFlightQueryKey = key;
		loading = true;
		try {
			const runData = await tracesApi.listTenant(query);
			if (requestId !== requestSequence) return;
			runs = runData;
			lastResolvedQueryKey = key;
			hasMore = runData.length >= PAGE_SIZE;
		} catch (err) {
			if (requestId !== requestSequence) return;
			toast.error(
				getErrorMessage(err, 'Nao foi possivel carregar o dashboard de observabilidade.')
			);
		} finally {
			if (requestId === requestSequence) {
				loading = false;
				inFlightQueryKey = null;
			}
		}
	}

	async function loadMore() {
		if (loadingMore || !hasMore) return;
		const newLimit = runs.length + PAGE_SIZE;
		const query = buildTraceQuery(newLimit);
		const key = queryKey(query);
		if (key === loadMoreQueryKey) return;

		loadingMore = true;
		loadMoreQueryKey = key;
		try {
			const data = await tracesApi.listTenant(query);
			const existingIds = new Set(runs.map((r) => r.run_id));
			for (const run of data) {
				if (!existingIds.has(run.run_id)) {
					runs = [...runs, run];
				}
			}
			if (data.length < newLimit) hasMore = false;
		} catch {
			hasMore = false;
		} finally {
			loadingMore = false;
			loadMoreQueryKey = null;
		}
	}

	async function openRunDetails(run: RunTraceListItem) {
		selectedRun = run;
		resolvedRunDetailsId = run.run_id;
		closingRunDetailsId = null;
		sheetOpen = true;
		setRunDetailsParam(run.run_id);
	}

	async function openRunDetailsById(runId: string) {
		const existing = runs.find((run) => run.run_id === runId);
		if (existing) {
			selectedRun = existing;
			resolvedRunDetailsId = runId;
			closingRunDetailsId = null;
			sheetOpen = true;
			return;
		}
		try {
			const response = await tracesApi.getTenantRun(runId);
			const run = runListItemFromTrace(response);
			selectedRun = run;
			resolvedRunDetailsId = runId;
			closingRunDetailsId = null;
			sheetOpen = true;
			if (!runs.some((item) => item.run_id === run.run_id)) {
				runs = [run, ...runs];
			}
		} catch (err) {
			toast.error(getErrorMessage(err, 'Nao foi possivel carregar o run trace selecionado.'));
			setRunDetailsParam(null);
		}
	}

	function setRunDetailsParam(runId: string | null) {
		const next = new URL(page.url);
		if (runId) {
			next.searchParams.set('runDetails', runId);
		} else {
			next.searchParams.delete('runDetails');
		}
		if (`${next.pathname}${next.search}` === `${page.url.pathname}${page.url.search}`) return;
		replaceState(`${next.pathname}${next.search}`, page.state);
	}

	function setSheetOpen(open: boolean) {
		sheetOpen = open;
		if (!open) closeRunDetails();
	}

	function closeRunDetails() {
		if (selectedRun) closingRunDetailsId = selectedRun.run_id;
		selectedRun = null;
		resolvedRunDetailsId = null;
		setRunDetailsParam(null);
	}

	function clearFilters() {
		const hadFilters = hasActiveFilters;
		agentFilter = 'all';
		searchQuery = '';
		dateRange = undefined;
		if (!hadFilters) void loadDashboard();
	}

	function buildTraceQuery(limit: number) {
		const params: {
			limit: number;
			started_from?: string;
			started_to?: string;
			instance_id?: string;
			q?: string;
		} = { limit };
		if (agentFilter !== 'all') params.instance_id = agentFilter;
		if (searchQuery.trim()) params.q = searchQuery.trim();
		if (dateRange?.start) params.started_from = dateRange.start.toDate('utc').toISOString();
		if (dateRange?.end) {
			const end = dateRange.end.toDate('utc');
			end.setUTCDate(end.getUTCDate() + 1);
			params.started_to = end.toISOString();
		}
		return params;
	}

	function applyFilters() {
		void loadDashboard();
	}

	function queryKey(params: TenantTraceListParams) {
		const query = new URLSearchParams();
		for (const [key, value] of Object.entries(params)) {
			if (value !== undefined && value !== null && value !== '') {
				query.set(key, String(value));
			}
		}
		query.sort();
		return query.toString();
	}

	function sum(
		items: RunTraceListItem[],
		key: 'total_tokens' | 'prompt_tokens' | 'completion_tokens' | 'embedding_tokens'
	) {
		return items.reduce((acc, item) => acc + (item[key] ?? 0), 0);
	}

	function runTotalTokens(run: RunTraceListItem) {
		return (run.total_tokens ?? 0) + (run.embedding_tokens ?? 0);
	}

	function buildInstanceSummaries(
		items: RunTraceListItem[],
		names: Map<string, string>
	): InstanceTokenSummary[] {
		const grouped = new Map<string, InstanceTokenSummary>();
		for (const run of items) {
			const current = grouped.get(run.instance_id) ?? {
				instance_id: run.instance_id,
				name: names.get(run.instance_id) ?? 'Unknown agent',
				runs: 0,
				total_tokens: 0,
				prompt_tokens: 0,
				completion_tokens: 0,
				embedding_tokens: 0,
				duration_ms: 0
			};
			current.runs += 1;
			current.total_tokens += runTotalTokens(run);
			current.prompt_tokens += run.prompt_tokens ?? 0;
			current.completion_tokens += run.completion_tokens ?? 0;
			current.embedding_tokens += run.embedding_tokens ?? 0;
			current.duration_ms += run.duration_ms;
			grouped.set(run.instance_id, current);
		}
		return [...grouped.values()].sort((a, b) => b.total_tokens - a.total_tokens);
	}

	function runListItemFromTrace(
		response: Awaited<ReturnType<typeof tracesApi.getTenantRun>>
	): RunTraceListItem {
		const trace = response.trace;
		return {
			run_id: response.run_id,
			instance_id: response.instance_id,
			session_id: response.session_id,
			started_at: response.started_at,
			completed_at: response.completed_at,
			duration_ms: trace.duration_ms,
			user_message: trace.user_message,
			final_response_preview: trace.final_response?.slice(0, 240) ?? null,
			total_tokens: trace.token_usage?.total_tokens ?? 0,
			prompt_tokens: trace.token_usage?.prompt_tokens ?? 0,
			completion_tokens: trace.token_usage?.completion_tokens ?? 0,
			embedding_tokens: trace.token_usage?.embedding_tokens ?? 0,
			embedding_calls: trace.token_usage?.embedding_calls ?? 0
		};
	}

	function fmtInt(value: number | null | undefined) {
		return new Intl.NumberFormat('en-US').format(value ?? 0);
	}

	function fmtDuration(ms: number) {
		if (ms < 1000) return `${ms}ms`;
		return `${(ms / 1000).toFixed(1)}s`;
	}

	function fmtDate(value: string) {
		return new Intl.DateTimeFormat('pt-BR', {
			day: '2-digit',
			month: '2-digit',
			hour: '2-digit',
			minute: '2-digit'
		}).format(new Date(value));
	}

	function pct(value: number, total: number) {
		if (total <= 0) return 0;
		return Math.max(3, Math.round((value / total) * 100));
	}
</script>

<div class="flex flex-col gap-3 p-4">
	<section class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
		<div class="min-h-[124px] border bg-card p-4">
			<div class="flex items-center justify-between">
				<span class="text-xs font-medium text-muted-foreground uppercase">Total tokens</span>
				<Zap class="size-4 text-purple-400" />
			</div>
			<p class="mt-3 font-mono text-2xl font-semibold">{fmtInt(totalTokens)}</p>
			<p class="mt-1 text-xs text-muted-foreground">
				{fmtInt(llmTokens)} LLM / {fmtInt(embeddingTokens)} embeddings
			</p>
		</div>
		<div class="min-h-[124px] border bg-card p-4">
			<div class="flex items-center justify-between">
				<span class="text-xs font-medium text-muted-foreground uppercase">Runs</span>
				<BarChart3 class="size-4 text-blue-400" />
			</div>
			<p class="mt-3 font-mono text-2xl font-semibold">{fmtInt(totalRuns)}</p>
			<p class="mt-1 text-xs text-muted-foreground">
				{fmtInt(runsWithTokens.length)} with token usage captured
			</p>
		</div>
		<div class="min-h-[124px] border bg-card p-4">
			<div class="flex items-center justify-between">
				<span class="text-xs font-medium text-muted-foreground uppercase">Avg tokens / run</span>
				<BarChart3 class="size-4 text-emerald-400" />
			</div>
			<p class="mt-3 font-mono text-2xl font-semibold">{fmtInt(averageTokens)}</p>
			<p class="mt-1 text-xs text-muted-foreground">
				Based on the latest {Math.min(totalRuns, runs.length)} runs
			</p>
		</div>
		<div class="min-h-[124px] border bg-card p-4">
			<div class="flex items-center justify-between">
				<span class="text-xs font-medium text-muted-foreground uppercase">Avg duration</span>
				<Clock3 class="size-4 text-amber-400" />
			</div>
			<p class="mt-3 font-mono text-2xl font-semibold">{fmtDuration(averageDuration)}</p>
			<p class="mt-1 text-xs text-muted-foreground">Execution time from persisted traces</p>
		</div>
	</section>

	<!-- Filters -->
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div class="flex max-w-4xl min-w-[300px] flex-1 flex-wrap items-center gap-2">
			<div class="relative w-full max-w-xs">
				<Search class="absolute top-2.5 left-2.5 size-4 text-muted-foreground" />
				<Input
					placeholder="Search messages..."
					bind:value={searchQuery}
					class="h-9 bg-background pl-9"
					onkeydown={(event) => {
						if (event.key === 'Enter') applyFilters();
					}}
				/>
			</div>

			<Select.Root type="single" bind:value={agentFilter}>
				<Select.Trigger class="min-h-9 w-[160px] bg-background">
					{agentOptions.find((o) => o.value === agentFilter)?.label ?? 'All Agents'}
				</Select.Trigger>
				<Select.Content>
					{#each agentOptions as option}
						<Select.Item value={option.value}>{option.label}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>

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

			<Button variant="outline" size="sm" class="h-9 bg-background" onclick={applyFilters}
				>Apply</Button
			>

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

		<Button
			variant="outline"
			size="sm"
			class="h-9 gap-2 bg-background"
			disabled={loading}
			onclick={() => loadDashboard({ force: true })}
		>
			<RefreshCw class={`size-4 ${loading ? 'animate-spin' : ''}`} />
			Refresh
		</Button>
	</div>

	<section class="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
		<div class="relative flex h-[620px] flex-col overflow-hidden border bg-card">
			{#if isRefetching}
				<div
					class="pointer-events-none absolute top-3 right-3 z-10 flex items-center gap-2 border bg-background/90 px-2.5 py-1.5 text-xs text-muted-foreground backdrop-blur"
				>
					<RefreshCw class="size-3 animate-spin" />
					Updating
				</div>
			{/if}
			<div class="min-h-0 flex-1 bg-card">
				<Table.Root
					containerClass="scrollbar-none h-full overflow-auto bg-card"
					class="min-w-[1008px] table-fixed text-sm"
				>
					<colgroup>
						<col class="w-[112px]" />
						<col class="w-[180px]" />
						<col class="w-[300px]" />
						<col class="w-[96px]" />
						<col class="w-[112px]" />
						<col class="w-[128px]" />
						<col class="w-[96px]" />
					</colgroup>
					<Table.Header
						class="sticky top-0 z-20 bg-background text-[11px] text-muted-foreground uppercase"
					>
						<Table.Row class="bg-background hover:bg-background">
							<Table.Head class="bg-background px-4 py-2 font-bold tracking-wider">Run</Table.Head>
							<Table.Head class="bg-background px-4 py-2 font-bold tracking-wider">Agent</Table.Head
							>
							<Table.Head class="bg-background px-4 py-2 font-bold tracking-wider"
								>Message</Table.Head
							>
							<Table.Head class="bg-background px-4 py-2 text-right font-bold tracking-wider"
								>Prompt</Table.Head
							>
							<Table.Head class="bg-background px-4 py-2 text-right font-bold tracking-wider"
								>Completion</Table.Head
							>
							<Table.Head class="bg-background px-4 py-2 text-right font-bold tracking-wider"
								>Total</Table.Head
							>
							<Table.Head class="bg-background px-4 py-2 text-right font-bold tracking-wider"
								>Duration</Table.Head
							>
						</Table.Row>
					</Table.Header>
					<Table.Body>
						{#if loading && filteredRuns.length === 0}
							{#each Array.from({ length: 6 }) as _, index (index)}
								<Table.Row class="bg-card">
									<Table.Cell class="px-4 py-4" colspan={7}>
										<div class="h-4 animate-pulse bg-muted"></div>
									</Table.Cell>
								</Table.Row>
							{/each}
						{:else if !loading && filteredRuns.length === 0}
							<Table.Row class="bg-card hover:bg-card">
								<Table.Cell class="px-4 py-10 text-center text-muted-foreground" colspan={7}>
									{hasActiveFilters
										? 'No runs match the current filters.'
										: 'No run traces have been captured yet.'}
								</Table.Cell>
							</Table.Row>
						{:else}
							{#each filteredRuns as run (run.run_id)}
								<!-- svelte-ignore a11y_no_noninteractive_element_to_interactive_role -->
								<Table.Row
									role="button"
									tabindex={0}
									class="cursor-pointer bg-card align-top hover:bg-muted/50"
									onclick={() => openRunDetails(run)}
									onkeydown={(e) => {
										if (e.key === 'Enter' || e.key === ' ') {
											e.preventDefault();
											void openRunDetails(run);
										}
									}}
								>
									<Table.Cell class="px-4 py-3">
										<div class="font-mono text-xs">{run.run_id.slice(0, 8)}</div>
										<div class="mt-1 text-xs text-muted-foreground">{fmtDate(run.started_at)}</div>
									</Table.Cell>
									<Table.Cell class="px-4 py-3">
										<div class="max-w-44 truncate font-medium">
											{instanceNames.get(run.instance_id) ?? 'Unknown agent'}
										</div>
										<div class="mt-1 font-mono text-[11px] text-muted-foreground">
											{run.instance_id.slice(0, 8)}
										</div>
									</Table.Cell>
									<Table.Cell class="px-4 py-3">
										<div class="line-clamp-2 text-xs whitespace-normal">
											{run.user_message ?? run.final_response_preview ?? 'No preview'}
										</div>
									</Table.Cell>
									<Table.Cell class="px-4 py-3 text-right font-mono text-blue-400"
										>{fmtInt(run.prompt_tokens)}</Table.Cell
									>
									<Table.Cell class="px-4 py-3 text-right font-mono text-emerald-400"
										>{fmtInt(run.completion_tokens)}</Table.Cell
									>
									<Table.Cell class="px-4 py-3 text-right">
										<div class="font-mono font-semibold text-purple-400">
											{fmtInt(runTotalTokens(run))}
										</div>
										<div class="mt-1 h-1.5 bg-muted">
											<div
												class="h-1.5 bg-purple-500"
												style={`width:${pct(runTotalTokens(run), maxRunTokens)}%`}
											></div>
										</div>
									</Table.Cell>
									<Table.Cell class="px-4 py-3 text-right font-mono"
										>{fmtDuration(run.duration_ms)}</Table.Cell
									>
								</Table.Row>
							{/each}
							{#if !loading && filteredRuns.length > 0}
								<Table.Row class="bg-card hover:bg-card">
									<Table.Cell colspan={7}>
										<div bind:this={sentinel} class="flex items-center justify-center py-4">
											{#if loadingMore}
												<div class="flex items-center gap-2 text-xs text-muted-foreground">
													<RefreshCw class="size-3 animate-spin" />
													Loading more...
												</div>
											{:else if !hasMore}
												<span class="text-xs text-muted-foreground">All runs loaded.</span>
											{/if}
										</div>
									</Table.Cell>
								</Table.Row>
							{/if}
						{/if}
					</Table.Body>
				</Table.Root>
			</div>
			<div class="border-t bg-card px-4 py-2">
				<p class="text-[10px] font-bold tracking-widest text-muted-foreground uppercase">
					Showing {filteredRuns.length} run traces
				</p>
			</div>
		</div>

		<aside class="space-y-4">
			<section class="min-h-[320px] border bg-card">
				<div class="border-b bg-muted/30 px-4 py-3">
					<h2 class="text-sm font-semibold">Usage by agent</h2>
					<p class="mt-1 text-xs text-muted-foreground">Sorted by total tokens.</p>
				</div>
				<div class="space-y-3 bg-card p-4">
					{#if loading && instanceSummaries.length === 0}
						{#each Array.from({ length: 4 }) as _, index (index)}
							<div class="h-14 animate-pulse bg-muted"></div>
						{/each}
					{:else if !loading && instanceSummaries.length === 0}
						<p class="py-6 text-center text-sm text-muted-foreground">No agent usage yet.</p>
					{:else}
						{#each instanceSummaries as item (item.instance_id)}
							<div class="space-y-2 bg-card">
								<div class="flex items-start justify-between gap-3">
									<div class="min-w-0">
										<div class="flex items-center gap-2">
											<Bot class="size-4 shrink-0 text-blue-400" />
											<p class="truncate text-sm font-medium">{item.name}</p>
										</div>
										<p class="mt-1 text-xs text-muted-foreground">
											{item.runs} run{item.runs === 1 ? '' : 's'} / avg {fmtInt(
												Math.round(item.total_tokens / item.runs)
											)} tok
										</p>
									</div>
									<div class="text-right font-mono text-sm font-semibold text-purple-400">
										{fmtInt(item.total_tokens)}
									</div>
								</div>
								<div class="h-2 bg-muted">
									<div
										class="h-2 bg-blue-500"
										style={`width:${pct(item.total_tokens, totalTokens)}%`}
									></div>
								</div>
							</div>
						{/each}
					{/if}
				</div>
			</section>

			<section class="border bg-card p-4">
				<h2 class="text-sm font-semibold">Token split</h2>
				<div class="mt-4 grid grid-cols-2 gap-3">
					<div class="border bg-blue-500/10 p-3">
						<p class="text-xs text-muted-foreground">Prompt</p>
						<p class="mt-2 font-mono text-lg font-semibold text-blue-400">{fmtInt(promptTokens)}</p>
					</div>
					<div class="border bg-emerald-500/10 p-3">
						<p class="text-xs text-muted-foreground">Completion</p>
						<p class="mt-2 font-mono text-lg font-semibold text-emerald-400">
							{fmtInt(completionTokens)}
						</p>
					</div>
					<div class="border bg-amber-500/10 p-3">
						<p class="text-xs text-muted-foreground">Embeddings</p>
						<p class="mt-2 font-mono text-lg font-semibold text-amber-400">
							{fmtInt(embeddingTokens)}
						</p>
					</div>
					<div class="border bg-purple-500/10 p-3">
						<p class="text-xs text-muted-foreground">All tracked</p>
						<p class="mt-2 font-mono text-lg font-semibold text-purple-400">
							{fmtInt(totalTokens)}
						</p>
					</div>
				</div>
			</section>
		</aside>
	</section>
</div>

<Sheet.Root bind:open={() => sheetOpen, setSheetOpen}>
	<Sheet.Content class="sm:!max-w-5xl" side="right">
		{#if selectedRun}
			<RunTracePanel
				instanceId={selectedRun.instance_id}
				sessionId={selectedRun.session_id}
				runId={selectedRun.run_id}
			/>
		{/if}
	</Sheet.Content>
</Sheet.Root>
