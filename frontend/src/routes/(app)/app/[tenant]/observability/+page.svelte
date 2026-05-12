<script lang="ts">
	import Activity from '@lucide/svelte/icons/activity';
	import AlertCircle from '@lucide/svelte/icons/alert-circle';
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
	import RangeCalendar from '$lib/components/ui/range-calendar/range-calendar.svelte';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
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
	let error = $state<string | null>(null);
	let hasMore = $state(data.hasMore);
	let sheetOpen = $state(false);
	let selectedRun = $state<RunTraceListItem | null>(null);
	let sentinel = $state<HTMLDivElement | null>(null);

	let agentFilter = $state('all');
	let searchQuery = $state('');
	let dateRangeOpen = $state(false);
	let dateRange = $state<{ start: DateValue | undefined; end: DateValue | undefined } | undefined>(undefined);
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

	const hasActiveFilters = $derived(agentFilter !== 'all' || searchQuery !== '' || dateRange !== undefined);
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

	async function loadDashboard(options: { force?: boolean } = {}) {
		const query = buildTraceQuery(PAGE_SIZE);
		const key = queryKey(query);
		if (!options.force && key === lastResolvedQueryKey) return;
		if (key === inFlightQueryKey) return;

		const requestId = ++requestSequence;
		inFlightQueryKey = key;
		loading = true;
		error = null;
		try {
			const runData = await tracesApi.listTenant(query);
			if (requestId !== requestSequence) return;
			runs = runData;
			lastResolvedQueryKey = key;
			hasMore = runData.length >= PAGE_SIZE;
		} catch (err) {
			if (requestId !== requestSequence) return;
			error = getErrorMessage(err, 'Nao foi possivel carregar o dashboard de observabilidade.');
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
			const current =
				grouped.get(run.instance_id) ??
				{
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

<div class="mx-auto max-w-7xl space-y-6 p-6">
	<header class="flex flex-col gap-4 border-b pb-5 md:flex-row md:items-center md:justify-between">
		<div class="flex items-center gap-3">
			<div class="flex size-10 items-center justify-center rounded-md bg-blue-500/10 text-blue-500">
				<Activity class="size-5" />
			</div>
			<div>
				<h1 class="font-display text-xl font-semibold" style="color:var(--text-main)">Observability</h1>
				<p class="mt-1 text-sm text-muted-foreground">
					Token consumption and run trace health across this tenant.
				</p>
			</div>
		</div>
		<button
			type="button"
			class="inline-flex h-9 items-center gap-2 rounded-md border px-3 text-sm font-medium hover:bg-muted disabled:opacity-60"
			disabled={loading}
			onclick={() => loadDashboard({ force: true })}
		>
			<RefreshCw class={`size-4 ${loading ? 'animate-spin' : ''}`} />
			Refresh
		</button>
	</header>

	{#if error}
		<section class="flex items-center gap-3 rounded-md border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
			<AlertCircle class="size-4 shrink-0" />
			<span>{error}</span>
		</section>
	{/if}

	<section class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
		<div class="min-h-[124px] rounded-md border p-4">
			<div class="flex items-center justify-between">
				<span class="text-xs font-medium uppercase text-muted-foreground">Total tokens</span>
				<Zap class="size-4 text-purple-400" />
			</div>
			<p class="mt-3 font-mono text-2xl font-semibold">{fmtInt(totalTokens)}</p>
			<p class="mt-1 text-xs text-muted-foreground">{fmtInt(llmTokens)} LLM / {fmtInt(embeddingTokens)} embeddings</p>
		</div>
		<div class="min-h-[124px] rounded-md border p-4">
			<div class="flex items-center justify-between">
				<span class="text-xs font-medium uppercase text-muted-foreground">Runs</span>
				<Activity class="size-4 text-blue-400" />
			</div>
			<p class="mt-3 font-mono text-2xl font-semibold">{fmtInt(totalRuns)}</p>
			<p class="mt-1 text-xs text-muted-foreground">{fmtInt(runsWithTokens.length)} with token usage captured</p>
		</div>
		<div class="min-h-[124px] rounded-md border p-4">
			<div class="flex items-center justify-between">
				<span class="text-xs font-medium uppercase text-muted-foreground">Avg tokens / run</span>
				<BarChart3 class="size-4 text-emerald-400" />
			</div>
			<p class="mt-3 font-mono text-2xl font-semibold">{fmtInt(averageTokens)}</p>
			<p class="mt-1 text-xs text-muted-foreground">Based on the latest {Math.min(totalRuns, runs.length)} runs</p>
		</div>
		<div class="min-h-[124px] rounded-md border p-4">
			<div class="flex items-center justify-between">
				<span class="text-xs font-medium uppercase text-muted-foreground">Avg duration</span>
				<Clock3 class="size-4 text-amber-400" />
			</div>
			<p class="mt-3 font-mono text-2xl font-semibold">{fmtDuration(averageDuration)}</p>
			<p class="mt-1 text-xs text-muted-foreground">Execution time from persisted traces</p>
		</div>
	</section>

	<!-- Filters -->
	<div class="flex flex-wrap items-center gap-2">
		<Select.Root type="single" bind:value={agentFilter}>
			<Select.Trigger class="min-h-9 w-[160px] bg-card">
				{agentOptions.find((o) => o.value === agentFilter)?.label ?? 'All Agents'}
			</Select.Trigger>
			<Select.Content>
				{#each agentOptions as option}
					<Select.Item value={option.value}>{option.label}</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>

		<div class="relative w-full max-w-xs">
			<Search class="absolute top-2.5 left-2.5 size-4 text-muted-foreground" />
			<Input
				placeholder="Search messages..."
				bind:value={searchQuery}
				class="h-9 pl-9"
				onkeydown={(event) => {
					if (event.key === 'Enter') applyFilters();
				}}
			/>
		</div>

		<Popover.Root bind:open={dateRangeOpen}>
			<Popover.Trigger>
				{#snippet child({ props })}
					<Button variant="outline" class="h-9 gap-2" {...props}>
						<CalendarIcon class="size-4" />
						<span class="text-xs">{dateRangeLabel}</span>
					</Button>
				{/snippet}
			</Popover.Trigger>
			<Popover.Content class="w-auto p-0" align="start">
				<RangeCalendar bind:value={dateRange} numberOfMonths={2} locale="pt-BR" />
				<div class="border-t p-2" style="border-color:var(--ds-border)">
					<Button class="w-full" size="sm" onclick={() => { dateRangeOpen = false; applyFilters(); }}>
						Apply range
					</Button>
				</div>
			</Popover.Content>
		</Popover.Root>

		<Button variant="outline" size="sm" class="h-9" onclick={applyFilters}>
			Apply
		</Button>

		{#if hasActiveFilters}
			<Button variant="ghost" size="sm" class="h-9 gap-1 text-muted-foreground" onclick={clearFilters}>
				<X class="size-4" />
				Clear
			</Button>
		{/if}
	</div>

	<section class="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
		<div class="relative min-h-[720px] rounded-md border">
			{#if isRefetching}
				<div class="pointer-events-none absolute top-3 right-3 z-10 flex items-center gap-2 rounded-md border bg-background/90 px-2.5 py-1.5 text-xs text-muted-foreground shadow-sm backdrop-blur">
					<RefreshCw class="size-3 animate-spin" />
					Updating
				</div>
			{/if}
			<div class="border-b px-4 py-3">
				<h2 class="text-sm font-semibold">Recent run token usage</h2>
				<p class="mt-1 text-xs text-muted-foreground">Each row is one persisted run trace.</p>
			</div>
			<div class="overflow-x-auto">
				<table class="w-full min-w-[900px] table-fixed text-sm">
					<colgroup>
						<col class="w-[112px]" />
						<col class="w-[180px]" />
						<col class="w-[96px]" />
						<col class="w-[112px]" />
						<col class="w-[112px]" />
						<col class="w-[128px]" />
						<col class="w-[96px]" />
						<col />
					</colgroup>
					<thead class="border-b text-xs uppercase text-muted-foreground">
						<tr>
							<th class="px-4 py-3 text-left font-medium">Run</th>
							<th class="px-4 py-3 text-left font-medium">Agent</th>
							<th class="px-4 py-3 text-right font-medium">Prompt</th>
							<th class="px-4 py-3 text-right font-medium">Completion</th>
							<th class="px-4 py-3 text-right font-medium">Embeddings</th>
							<th class="px-4 py-3 text-right font-medium">Total</th>
							<th class="px-4 py-3 text-right font-medium">Duration</th>
							<th class="px-4 py-3 text-left font-medium">Message</th>
						</tr>
					</thead>
					<tbody>
						{#if loading && filteredRuns.length === 0}
							{#each Array.from({ length: 6 }) as _, index (index)}
								<tr class="border-b">
									<td class="px-4 py-4" colspan="8">
										<div class="h-4 animate-pulse rounded bg-muted"></div>
									</td>
								</tr>
							{/each}
						{:else if !loading && filteredRuns.length === 0}
							<tr>
								<td class="px-4 py-10 text-center text-muted-foreground" colspan="8">
									{hasActiveFilters ? 'No runs match the current filters.' : 'No run traces have been captured yet.'}
								</td>
							</tr>
						{:else}
							{#each filteredRuns as run (run.run_id)}
								<!-- svelte-ignore a11y_no_noninteractive_element_to_interactive_role -->
								<tr
									role="button"
									tabindex="0"
									class="cursor-pointer border-b align-top hover:bg-muted/40"
									onclick={() => {
										selectedRun = run;
										sheetOpen = true;
									}}
									onkeydown={(e) => {
										if (e.key === 'Enter' || e.key === ' ') {
											e.preventDefault();
											selectedRun = run;
											sheetOpen = true;
										}
									}}
								>
									<td class="px-4 py-3">
										<div class="font-mono text-xs">{run.run_id.slice(0, 8)}</div>
										<div class="mt-1 text-xs text-muted-foreground">{fmtDate(run.started_at)}</div>
									</td>
									<td class="px-4 py-3">
										<div class="max-w-44 truncate font-medium">{instanceNames.get(run.instance_id) ?? 'Unknown agent'}</div>
										<div class="mt-1 font-mono text-[11px] text-muted-foreground">{run.instance_id.slice(0, 8)}</div>
									</td>
									<td class="px-4 py-3 text-right font-mono text-blue-400">{fmtInt(run.prompt_tokens)}</td>
									<td class="px-4 py-3 text-right font-mono text-emerald-400">{fmtInt(run.completion_tokens)}</td>
									<td class="px-4 py-3 text-right font-mono text-amber-400">{fmtInt(run.embedding_tokens)}</td>
									<td class="px-4 py-3 text-right">
										<div class="font-mono font-semibold text-purple-400">{fmtInt(runTotalTokens(run))}</div>
										<div class="mt-1 h-1.5 rounded bg-muted">
											<div class="h-1.5 rounded bg-purple-500" style={`width:${pct(runTotalTokens(run), maxRunTokens)}%`}></div>
										</div>
									</td>
									<td class="px-4 py-3 text-right font-mono">{fmtDuration(run.duration_ms)}</td>
									<td class="px-4 py-3">
										<div class="line-clamp-2 max-w-72 text-xs">{run.user_message ?? run.final_response_preview ?? 'No preview'}</div>
									</td>
								</tr>
							{/each}
							{#if !loading && filteredRuns.length > 0}
								<tr>
									<td colspan="8">
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
									</td>
								</tr>
							{/if}
						{/if}
					</tbody>
				</table>
			</div>
		</div>

		<aside class="space-y-4">
			<section class="min-h-[320px] rounded-md border">
				<div class="border-b px-4 py-3">
					<h2 class="text-sm font-semibold">Usage by agent</h2>
					<p class="mt-1 text-xs text-muted-foreground">Sorted by total tokens.</p>
				</div>
				<div class="space-y-3 p-4">
					{#if loading && instanceSummaries.length === 0}
						{#each Array.from({ length: 4 }) as _, index (index)}
							<div class="h-14 animate-pulse rounded bg-muted"></div>
						{/each}
					{:else if !loading && instanceSummaries.length === 0}
						<p class="py-6 text-center text-sm text-muted-foreground">No agent usage yet.</p>
					{:else}
						{#each instanceSummaries as item (item.instance_id)}
							<div class="space-y-2">
								<div class="flex items-start justify-between gap-3">
									<div class="min-w-0">
										<div class="flex items-center gap-2">
											<Bot class="size-4 shrink-0 text-blue-400" />
											<p class="truncate text-sm font-medium">{item.name}</p>
										</div>
										<p class="mt-1 text-xs text-muted-foreground">{item.runs} run{item.runs === 1 ? '' : 's'} / avg {fmtInt(Math.round(item.total_tokens / item.runs))} tok</p>
									</div>
									<div class="text-right font-mono text-sm font-semibold text-purple-400">
										{fmtInt(item.total_tokens)}
									</div>
								</div>
								<div class="h-2 rounded bg-muted">
									<div class="h-2 rounded bg-blue-500" style={`width:${pct(item.total_tokens, totalTokens)}%`}></div>
								</div>
							</div>
						{/each}
					{/if}
				</div>
			</section>

			<section class="rounded-md border p-4">
				<h2 class="text-sm font-semibold">Token split</h2>
				<div class="mt-4 grid grid-cols-2 gap-3">
					<div class="rounded-md bg-blue-500/10 p-3">
						<p class="text-xs text-muted-foreground">Prompt</p>
						<p class="mt-2 font-mono text-lg font-semibold text-blue-400">{fmtInt(promptTokens)}</p>
					</div>
					<div class="rounded-md bg-emerald-500/10 p-3">
						<p class="text-xs text-muted-foreground">Completion</p>
						<p class="mt-2 font-mono text-lg font-semibold text-emerald-400">{fmtInt(completionTokens)}</p>
					</div>
					<div class="rounded-md bg-amber-500/10 p-3">
						<p class="text-xs text-muted-foreground">Embeddings</p>
						<p class="mt-2 font-mono text-lg font-semibold text-amber-400">{fmtInt(embeddingTokens)}</p>
					</div>
					<div class="rounded-md bg-purple-500/10 p-3">
						<p class="text-xs text-muted-foreground">All tracked</p>
						<p class="mt-2 font-mono text-lg font-semibold text-purple-400">{fmtInt(totalTokens)}</p>
					</div>
				</div>
			</section>
		</aside>
	</section>
</div>

<Sheet.Root bind:open={sheetOpen}>
	<Sheet.Content class="sm:!max-w-5xl" side="right">
		{#if selectedRun}
			<RunTracePanel instanceId={selectedRun.instance_id} sessionId={selectedRun.session_id} runId={selectedRun.run_id} />
		{/if}
	</Sheet.Content>
</Sheet.Root>
