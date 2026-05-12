<script lang="ts">
	import { untrack, type Component } from 'svelte';
	import { SvelteFlow, Background, Controls } from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';
	import Bot from '@lucide/svelte/icons/bot';
	import Database from '@lucide/svelte/icons/database';
	import FileText from '@lucide/svelte/icons/file-text';
	import Wrench from '@lucide/svelte/icons/wrench';
	import GitBranch from '@lucide/svelte/icons/git-branch';
	import Layers from '@lucide/svelte/icons/layers';
	import MessageSquare from '@lucide/svelte/icons/message-square';
	import MessagesSquare from '@lucide/svelte/icons/messages-square';
	import User from '@lucide/svelte/icons/user';
	import X from '@lucide/svelte/icons/x';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { mode } from 'mode-watcher';
	import { tracesApi } from '$lib/api/chat';
	import { chatSessionStore } from '$lib/stores/chat-session.svelte';
	import { ApiError, getErrorMessage } from '$lib/api/client';
	import type { RunTracePayload, RunTraceResponse, RunTraceListItem } from '$lib/api/types';

	let {
		instanceId,
		sessionId: propSessionId,
		runId: propRunId
	}: { instanceId: string; sessionId?: string | null; runId?: string | null } = $props();

	let loading = $state(false);
	let error = $state('');
	let trace = $state<RunTracePayload | null>(null);
	let metadata = $state<RunTraceResponse | null>(null);
	let selectedNode = $state<string | null>(null);

	let runs = $state<RunTraceListItem[]>([]);
	let selectedRunId = $state<string | null>(null);
	let listLoading = $state(false);

	const isStaticMode = $derived(propSessionId !== undefined && propSessionId !== null);
	const isDark = $derived(mode.current === 'dark');

	const debSessId = $derived(chatSessionStore.sessionId(instanceId));
	const debRunId = $derived(chatSessionStore.lastRunId(instanceId));

	const reloadKey = $derived(
		propRunId
			? `${instanceId}-${propRunId}`
			: isStaticMode
				? `${instanceId}-${propSessionId}`
				: `${instanceId}-${debSessId}-${debRunId}`
	);

	const sessionTotalTokens = $derived(
		runs.reduce((sum, r) => sum + listItemTrackedTokens(r), 0)
	);

	$effect(() => {
		reloadKey;
		untrack(() => {
			void load();
		});
	});

	async function load(): Promise<void> {
		const sessionId = isStaticMode ? propSessionId! : chatSessionStore.sessionId(instanceId);
		const lastRunId = isStaticMode ? null : chatSessionStore.lastRunId(instanceId);
		const targetRunId = propRunId ?? lastRunId;

		await listRuns(sessionId);

		loading = true;
		error = '';
		try {
			let response: RunTraceResponse;
			if (targetRunId) {
				try {
					response = await tracesApi.get(instanceId, targetRunId);
				} catch (err) {
					if (!(err instanceof ApiError) || err.status !== 404) throw err;
					response = await tracesApi.getLatest(instanceId, sessionId);
				}
			} else {
				response = await tracesApi.getLatest(instanceId, sessionId);
			}
			metadata = response;
			trace = response.trace;
			selectedRunId = response.run_id;
		} catch (err) {
			if (err instanceof ApiError && err.status === 404) {
				error = isStaticMode
					? 'No traces found for this session.'
					: 'No trace found. Send a message in the Test Agent panel.';
			} else {
				error = getErrorMessage(err, 'Failed to load trace.');
			}
			trace = null;
			metadata = null;
		} finally {
			loading = false;
		}
	}

	async function listRuns(sessionId: string | null): Promise<void> {
		if (!sessionId) {
			runs = [];
			return;
		}
		listLoading = true;
		try {
			runs = await tracesApi.list(instanceId, sessionId, 100);
			runs.sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());
		} catch {
			runs = [];
		} finally {
			listLoading = false;
		}
	}

	async function selectRun(runId: string): Promise<void> {
		if (runId === selectedRunId) return;
		loading = true;
		error = '';
		try {
			const response = await tracesApi.get(instanceId, runId);
			metadata = response;
			trace = response.trace;
			selectedRunId = runId;
		} catch (err) {
			error = getErrorMessage(err, 'Failed to load trace.');
			trace = null;
			metadata = null;
		} finally {
			loading = false;
		}
	}

	function fmtMs(ms: number): string {
		if (ms < 1000) return `${ms} ms`;
		return `${(ms / 1000).toFixed(2)} s`;
	}

	function fmtScore(score?: number | null): string {
		if (typeof score !== 'number') return '—';
		return score.toFixed(3);
	}

	function fmtJson(value: unknown): string {
		if (value === null || value === undefined) return '—';
		try {
			return JSON.stringify(value, null, 2);
		} catch {
			return String(value);
		}
	}

	function parseMaybeJson(value: unknown): unknown {
		if (typeof value !== 'string') return value;
		const trimmed = value.trim();
		if (!trimmed) return value;
		const first = trimmed[0];
		if (first !== '{' && first !== '[' && first !== '"') return value;
		try {
			return JSON.parse(trimmed);
		} catch {
			return value;
		}
	}

	function isEmptyArgs(value: unknown): boolean {
		if (value === null || value === undefined) return true;
		if (typeof value === 'object' && !Array.isArray(value)) {
			return Object.keys(value as Record<string, unknown>).length === 0;
		}
		return false;
	}

	function extractHttpStatus(output: unknown): number | null {
		const parsed = parseMaybeJson(output) as { status?: unknown } | null;
		if (parsed && typeof parsed === 'object' && typeof parsed.status === 'number') {
			return parsed.status;
		}
		return null;
	}

	function extractHttpData(output: unknown): unknown {
		const parsed = parseMaybeJson(output);
		if (parsed && typeof parsed === 'object' && parsed !== null && 'data' in parsed) {
			return (parsed as { data: unknown }).data;
		}
		return parsed;
	}

	function statusBadgeClass(status: number | null): string {
		if (status === null) return 'bg-zinc-500/10 text-muted-foreground';
		if (status >= 200 && status < 300) return 'bg-emerald-500/10 text-emerald-400';
		if (status >= 300 && status < 400) return 'bg-blue-500/10 text-blue-400';
		if (status >= 400 && status < 500) return 'bg-amber-500/10 text-amber-400';
		return 'bg-red-500/10 text-red-400';
	}

	function approxBytes(value: unknown): number {
		if (value === null || value === undefined) return 0;
		try {
			return typeof value === 'string' ? value.length : JSON.stringify(value).length;
		} catch {
			return 0;
		}
	}

	function fmtBytes(n: number): string {
		if (n < 1024) return `${n} B`;
		if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
		return `${(n / (1024 * 1024)).toFixed(1)} MB`;
	}

	function listItemTrackedTokens(run: RunTraceListItem): number {
		return (run.total_tokens ?? 0) + (run.embedding_tokens ?? 0);
	}

	function traceTrackedTokens(t: RunTracePayload): number {
		if (!t.token_usage) return 0;
		return (t.token_usage.total_tokens ?? 0) + (t.token_usage.embedding_tokens ?? 0);
	}

	function listItemTokenTitle(run: RunTraceListItem): string {
		return [
			`prompt ${run.prompt_tokens ?? 0}`,
			`completion ${run.completion_tokens ?? 0}`,
			`embeddings ${run.embedding_tokens ?? 0}`,
			`embedding calls ${run.embedding_calls ?? 0}`
		].join(' / ');
	}

	function fmtTokens(n: number | null | undefined): string {
		if (n == null) return '—';
		if (n < 1000) return String(n);
		return `${(n / 1000).toFixed(1)}k`;
	}

	function fmtTime(value: string): string {
		return new Date(value).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
	}

	function timingFor(nodeName: string): number | null {
		const t = trace;
		if (!t) return null;
		const matches = (t.node_timings ?? []).filter((entry) => entry.name === nodeName);
		if (matches.length === 0) return null;
		return matches.reduce((acc, item) => acc + item.duration_ms, 0);
	}

	type NodeDescriptor = {
		id: string;
		label: string;
		icon: Component;
		tone: string;
		duration: number | null;
	};

	const executedCalls = $derived.by(() => {
		const t = trace;
		if (!t) return [];
		const list = t.executed_tool_calls ?? [];
		if (list.length > 0) return list;
		const availableSkills = new Set(t.available_skills ?? []);
		const pendingByName = new Map<string, (typeof t.pending_tool_calls)[number]>();
		for (const p of t.pending_tool_calls ?? []) {
			if (p.name) pendingByName.set(p.name, p);
		}
		return (t.tool_results ?? []).map((r) => {
			const name = r.name ?? '';
			const pending = pendingByName.get(name);
			return {
				id: r.id ?? null,
				name,
				kind: availableSkills.has(name) ? 'skill' : 'tool',
				arguments: pending?.arguments ?? null,
				output: r.output,
				error: r.error,
				iteration: null
			} as const;
		});
	});
	const skillCalls = $derived(executedCalls.filter((c) => c.kind === 'skill'));
	const toolCalls = $derived(executedCalls.filter((c) => c.kind === 'tool'));

	const activeNodes = $derived.by(() => {
		const t = trace;
		if (!t) return [] as NodeDescriptor[];
		const list: NodeDescriptor[] = [];
		list.push({ id: 'user', label: 'User message', icon: User, tone: 'neutral', duration: null });

		let llmLabel = `LLM · ${t.model ?? '?'}`;
		const badges: string[] = [];
		const trackedTokens = traceTrackedTokens(t);
		if (trackedTokens > 0) {
			badges.push(`${fmtTokens(trackedTokens)} tok`);
		}
		if (t.retrieved_chunks.length > 0) {
			badges.push(`RAG ${t.retrieved_chunks.length}`);
		}
		if (skillCalls.length > 0) {
			badges.push(`${skillCalls.length} skill${skillCalls.length > 1 ? 's' : ''}`);
		}
		if (toolCalls.length > 0) {
			badges.push(`${toolCalls.length} tool${toolCalls.length > 1 ? 's' : ''}`);
		}
		if (badges.length > 0) {
			llmLabel += `\n${badges.join(' · ')}`;
		}

		list.push({
			id: 'llm',
			label: llmLabel,
			icon: Bot,
			tone: 'used',
			duration: timingFor('llm')
		});

		if (t.handoff_target) {
			list.push({
				id: 'handoff',
				label: `Handoff · #${t.handoff_target.slice(0, 6)}`,
				icon: GitBranch,
				tone: 'warn',
				duration: timingFor('handoff')
			});
		}

		list.push({
			id: 'respond',
			label: 'Final response',
			icon: MessageSquare,
			tone: 'ok',
			duration: t.duration_ms
		});
		return list;
	});

	function tonePalette(tone: string): { bg: string; border: string; text: string } {
		switch (tone) {
			case 'used':
				return { bg: '#1e3a8a', border: '#3b82f6', text: '#ffffff' };
			case 'ok':
				return { bg: '#064e3b', border: '#10b981', text: '#ffffff' };
			case 'warn':
				return { bg: '#451a03', border: '#f59e0b', text: '#fbbf24' };
			default:
				return { bg: '#18181b', border: '#3f3f46', text: '#e4e4e7' };
		}
	}

	const flowData = $derived.by(() => {
		const list = activeNodes;
		const nodes = list.map((node, idx) => {
			const p = tonePalette(node.tone);
			const selected = node.id === selectedNode;
			const label = node.duration != null ? `${node.label}\n${fmtMs(node.duration)}` : node.label;
			return {
				id: node.id,
				type: idx === 0 ? 'input' : idx === list.length - 1 ? 'output' : 'default',
				data: { label },
				position: { x: 0, y: idx * 110 },
				style: `background:${p.bg};border:2px solid ${selected ? '#ffffff' : p.border};color:${p.text};border-radius:10px;padding:10px 14px;font-size:11px;font-weight:600;min-width:200px;text-align:center;box-shadow:${selected ? '0 0 0 3px rgba(255,255,255,0.15)' : '0 4px 12px rgba(0,0,0,0.3)'}`
			};
		});
		const edges = list.slice(0, -1).map((node, idx) => ({
			id: `e-${node.id}-${list[idx + 1].id}`,
			source: node.id,
			target: list[idx + 1].id,
			animated: true,
			style: 'stroke:#52525b;stroke-width:1.5',
			markerEnd: { type: 'arrowclosed' as const, color: '#52525b' }
		}));
		return { nodes, edges };
	});

	function handleNodeClick(detail: { node: { id: string } }): void {
		const id = detail?.node?.id;
		if (!id) return;
		selectedNode = selectedNode === id ? null : id;
	}
</script>

{#snippet detailHeader(title: string, subtitle: string, Icon: Component)}
	<div class="mb-4 flex items-start justify-between gap-3">
		<div class="flex items-start gap-3">
			<div
				class="flex size-9 items-center justify-center rounded-lg"
				style="background:color-mix(in srgb,#3b82f6 12%,transparent);border:1px solid color-mix(in srgb,#3b82f6 28%,transparent)"
			>
				<Icon class="size-4 text-blue-400" />
			</div>
			<div>
				<h3 class="text-sm leading-tight font-semibold" style="color:var(--text-main)">{title}</h3>
				<p class="text-[11px] text-muted-foreground">{subtitle}</p>
			</div>
		</div>
		<button
			type="button"
			onclick={() => (selectedNode = null)}
			class="rounded-md p-1 text-muted-foreground transition-colors hover:bg-[var(--surface-hover)] hover:text-foreground"
			aria-label="Close details"
		>
			<X class="size-3.5" />
		</button>
	</div>
{/snippet}

{#if !isStaticMode && !debSessId}
	<div class="flex h-full flex-col items-center justify-center gap-4 p-6 text-center">
		<div
			class="flex size-16 items-center justify-center rounded-2xl"
			style="background:color-mix(in srgb,#3b82f6 12%,transparent);border:1px solid color-mix(in srgb,#3b82f6 28%,transparent)"
		>
			<Layers class="size-7 text-blue-400" />
		</div>
		<h2 class="text-lg font-semibold" style="color:var(--text-main)">Run Trace</h2>
		<p class="max-w-sm text-sm text-muted-foreground">
			Start a conversation in the <strong>Test Agent</strong> panel to inspect traces, node timings, and
			outputs here.
		</p>
		<p class="text-xs text-muted-foreground/60">
			Each message you send generates a trace with full execution details.
		</p>
	</div>
{:else}
	<div class="relative flex h-full flex-col overflow-hidden">
		<header
			class="flex items-center justify-between border-b px-6 py-4"
			style="border-color:var(--ds-border);background:var(--surface)"
		>
			<div class="flex items-center gap-3">
				<div
					class="flex size-9 items-center justify-center rounded-lg"
					style="background:color-mix(in srgb,#3b82f6 15%,transparent);border:1px solid color-mix(in srgb,#3b82f6 30%,transparent)"
				>
					<Layers class="size-4 text-blue-400" />
				</div>
				<div>
					<h2 class="text-sm leading-tight font-semibold" style="color:var(--text-main)">
						Run Trace
					</h2>
					<p class="text-[11px] text-muted-foreground">
						{metadata ? 'Trace of the selected message' : 'No trace loaded'}
					</p>
				</div>
			</div>
			<div class="flex items-center gap-3">
				{#if runs.length > 0}
					<span class="text-[11px] text-muted-foreground">
						{runs.length} message{runs.length !== 1 ? 's' : ''}
						{#if sessionTotalTokens > 0}
							<span class="opacity-50"> · </span>
							<span class="font-mono text-purple-400" title="Total LLM and embedding token consumption across all messages in this session">{fmtTokens(sessionTotalTokens)} tok</span>
						{/if}
					</span>
				{/if}
				{#if !isStaticMode && debSessId}
					<span
						class="rounded-full bg-emerald-500/10 px-2.5 py-1 text-[10px] font-semibold tracking-wider text-emerald-400 uppercase"
						title="Active session in Test Agent"
					>
						● live
					</span>
				{/if}
			</div>
		</header>

		<div class="flex min-h-0 flex-1 flex-col">
			<div class="flex min-h-0 flex-1">
				<!-- Message history sidebar -->
				{#if runs.length > 0}
					<aside
						class="w-[220px] shrink-0 overflow-y-auto border-r"
						style="border-color:var(--ds-border);background:var(--surface)"
					>
						<div
							class="sticky top-0 border-b bg-[var(--surface)] px-3 py-2 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase"
							style="border-color:var(--ds-border)"
						>
							Messages
						</div>
						{#each runs as run, idx (run.run_id)}
							<button
								type="button"
								onclick={() => selectRun(run.run_id)}
								style="border-color:var(--ds-border)"
								class="w-full border-b px-3 py-2.5 text-left transition-colors hover:bg-[var(--surface-hover)] {run.run_id ===
								selectedRunId
									? 'bg-[var(--surface-hover)]'
									: ''}"
							>
								<div class="flex items-center justify-between gap-2">
									<div class="flex items-center gap-2 min-w-0">
										<span
											class="flex size-5 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold"
											style="background:color-mix(in srgb, #3b82f6 12%, transparent);color:var(--text-main)"
										>
											{idx + 1}
										</span>
										<span class="truncate font-mono text-[10px] text-muted-foreground">
											{fmtTime(run.started_at)}
										</span>
									</div>
									{#if listItemTrackedTokens(run) > 0}
										<span class="shrink-0 rounded bg-purple-500/10 px-1.5 py-0.5 font-mono text-[9px] text-purple-400" title={listItemTokenTitle(run)}>
											{fmtTokens(listItemTrackedTokens(run))} tok
										</span>
									{/if}
								</div>
								<p class="mt-1 truncate text-[11px] leading-tight text-foreground/80">
									{run.user_message ?? run.final_response_preview ?? '—'}
								</p>
							</button>
						{/each}
					</aside>
				{/if}

				<!-- Main content -->
				<div class="flex flex-1 flex-col">
				{#if loading && !trace}
					<div class="flex flex-1 items-center justify-center text-sm text-muted-foreground">
						<Spinner class="mr-2 size-4" />
						Loading trace…
					</div>
				{:else if error}
					<div class="flex flex-1 items-center justify-center px-6">
						<div
							class="max-w-md rounded-xl border bg-[var(--canvas)] p-6 text-center text-sm"
							style="border-color:var(--ds-border)"
						>
							<Bot class="mx-auto mb-3 size-8 text-muted-foreground" />
							<p>{error}</p>
						</div>
					</div>
				{:else if trace && metadata}
					<div class="flex min-h-0 flex-1">
						<div
							class="relative h-full w-[320px] shrink-0 border-r"
							style="border-color:var(--ds-border);background:var(--canvas)"
						>
							<SvelteFlow
								nodes={flowData.nodes}
								edges={flowData.edges}
								fitView
								proOptions={{ hideAttribution: true }}
								nodesDraggable={false}
								nodesConnectable={false}
								elementsSelectable
								panOnDrag={false}
								onnodeclick={handleNodeClick}
							>
								<Background
									bgColor={isDark ? '#050505' : '#f8fafc'}
									gap={20}
									patternColor={isDark ? '#27272a' : '#d4d4d8'}
								/>
								<Controls position="bottom-right" showLock={false} />
							</SvelteFlow>
						</div>

						<div class="flex-1 overflow-y-auto p-6 pb-8">
							{#if !selectedNode}
								<div class="flex h-full items-center justify-center text-center">
									<div class="max-w-sm">
										<Bot class="mx-auto mb-3 size-8 text-muted-foreground" />
										<p class="text-sm text-muted-foreground">
											Click a node in the flow to inspect its input, output, and context.
										</p>
									</div>
								</div>
							{:else if selectedNode === 'user'}
								{@render detailHeader('User message', 'Run input', User)}
								<div
									class="rounded-xl border bg-[var(--canvas)] p-4 text-sm leading-relaxed"
									style="border-color:var(--ds-border)"
								>
									{trace.user_message || '—'}
								</div>
							{:else if selectedNode === 'llm'}
								{@render detailHeader(
									'LLM',
									`${trace.model ?? '?'} · ${trace.ai_provider ?? '?'} · temperature ${trace.temperature?.toFixed?.(2) ?? '—'}`,
									Bot
								)}
								<div class="space-y-3">
									{#if trace.token_usage}
										<div
											class="rounded-xl border bg-[var(--canvas)] p-3"
											style="border-color:var(--ds-border)"
										>
											<p class="mb-2 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase">
												Token Usage ({trace.token_usage.llm_calls} LLM call{trace.token_usage.llm_calls === 1 ? '' : 's'})
											</p>
											<div class="grid grid-cols-3 gap-2 text-xs">
												<div class="rounded-md bg-blue-500/10 p-2">
													<p class="text-[10px] text-muted-foreground uppercase tracking-wider">Prompt</p>
													<p class="font-mono text-base font-semibold text-blue-400">{fmtTokens(trace.token_usage.prompt_tokens)}</p>
												</div>
												<div class="rounded-md bg-emerald-500/10 p-2">
													<p class="text-[10px] text-muted-foreground uppercase tracking-wider">Completion</p>
													<p class="font-mono text-base font-semibold text-emerald-400">{fmtTokens(trace.token_usage.completion_tokens)}</p>
												</div>
												<div class="rounded-md bg-purple-500/10 p-2">
													<p class="text-[10px] text-muted-foreground uppercase tracking-wider">Total</p>
													<p class="font-mono text-base font-semibold text-purple-400">{fmtTokens(trace.token_usage.total_tokens)}</p>
												</div>
											</div>
											{#if trace.token_usage.embedding_tokens > 0}
												<div class="mt-2 flex items-center gap-2 rounded-md bg-amber-500/10 p-2 text-xs">
													<Database class="size-3 text-amber-400" />
													<span class="text-[11px] text-muted-foreground">Embeddings ({trace.token_usage.embedding_calls} call):</span>
													<span class="font-mono text-amber-400">{fmtTokens(trace.token_usage.embedding_tokens)} tok</span>
												</div>
											{/if}
											{#if trace.token_usage.per_call.length > 1}
												<details class="mt-2">
													<summary class="cursor-pointer text-[10px] font-semibold tracking-wider text-muted-foreground uppercase">
														Per-call breakdown ({trace.token_usage.per_call.length})
													</summary>
													<table class="mt-2 w-full font-mono text-[11px]">
														<thead>
															<tr class="text-muted-foreground/70">
																<th class="text-left">Iter</th>
																<th class="text-left">Phase</th>
																<th class="text-right">Prompt</th>
																<th class="text-right">Compl</th>
																<th class="text-right">Total</th>
															</tr>
														</thead>
														<tbody>
															{#each trace.token_usage.per_call as call, idx (idx)}
																<tr class="border-t" style="border-color:var(--ds-border)">
																	<td class="py-1">{call.iteration ?? 0}</td>
																	<td class="py-1 text-muted-foreground/80">{call.phase ?? '—'}</td>
																	<td class="py-1 text-right text-blue-400">{fmtTokens(call.prompt_tokens)}</td>
																	<td class="py-1 text-right text-emerald-400">{fmtTokens(call.completion_tokens)}</td>
																	<td class="py-1 text-right text-purple-400">{fmtTokens(call.total_tokens)}</td>
																</tr>
															{/each}
														</tbody>
													</table>
												</details>
											{/if}
										</div>
									{/if}
									{#if toolCalls.length > 0}
										<details class="rounded-xl border bg-[var(--canvas)]" style="border-color:var(--ds-border)" open>
											<summary class="flex cursor-pointer items-center gap-2 px-3 py-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
												<Wrench class="size-3.5 text-blue-400" />
												Tool calls ({toolCalls.length} call{toolCalls.length > 1 ? 's' : ''})
											</summary>
											<div class="border-t p-3" style="border-color:var(--ds-border)">
												<ol class="space-y-3">
													{#each toolCalls as call, idx (idx)}
														{@const parsedArgs = parseMaybeJson(call.arguments)}
														{@const httpStatus = extractHttpStatus(call.output)}
														{@const httpData = extractHttpData(call.output)}
														{@const outputBytes = approxBytes(call.output)}
														<li class="overflow-hidden rounded-xl border bg-[var(--canvas)]" style="border-color:var(--ds-border)">
															<header class="flex flex-wrap items-center justify-between gap-2 border-b px-3 py-2" style="border-color:var(--ds-border);background:var(--surface-hover)">
																<div class="flex items-center gap-2 min-w-0">
																	<span class="flex size-6 shrink-0 items-center justify-center rounded-md" style="background:color-mix(in srgb,#3b82f6 15%,transparent);border:1px solid color-mix(in srgb,#3b82f6 30%,transparent)">
																		<Wrench class="size-3 text-blue-400" />
																	</span>
																	<span class="font-mono text-xs font-semibold text-blue-400 truncate">{call.name ?? '(unnamed)'}</span>
																</div>
																<div class="flex items-center gap-1.5">
																	{#if httpStatus !== null}
																		<span class="rounded px-1.5 py-0.5 font-mono text-[10px] {statusBadgeClass(httpStatus)}">HTTP {httpStatus}</span>
																	{/if}
																	{#if outputBytes > 0}
																		<span class="rounded bg-zinc-500/10 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">{fmtBytes(outputBytes)}</span>
																	{/if}
																	{#if call.iteration != null}
																		<span class="rounded bg-zinc-500/10 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">iter {call.iteration}</span>
																	{/if}
																</div>
															</header>
															<div class="space-y-3 p-3">
																<div>
																	<p class="mb-1 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase">Arguments</p>
																	{#if isEmptyArgs(parsedArgs)}
																		<p class="text-[11px] text-muted-foreground/60 italic">(no arguments)</p>
																	{:else}
																		<pre class="overflow-x-auto rounded-md bg-zinc-500/5 p-2 font-mono text-[11px] leading-relaxed text-foreground/80">{fmtJson(parsedArgs)}</pre>
																	{/if}
																</div>
																{#if call.error}
																	<div>
																		<p class="mb-1 text-[10px] font-semibold tracking-wider text-red-400 uppercase">Error</p>
																		<p class="rounded-md bg-red-500/5 p-2 text-[11px] text-red-400">{call.error}</p>
																	</div>
																{:else if call.output !== undefined && call.output !== null}
																	<details class="group" open={outputBytes < 2000}>
																		<summary class="mb-1 flex cursor-pointer items-center justify-between text-[10px] font-semibold tracking-wider text-muted-foreground uppercase">
																			<span>Output</span>
																			<span class="text-muted-foreground/60 normal-case">click to toggle</span>
																		</summary>
																		<pre class="max-h-[400px] overflow-auto rounded-md bg-zinc-500/5 p-2 font-mono text-[11px] leading-relaxed text-foreground/80">{fmtJson(httpData)}</pre>
																	</details>
																{/if}
															</div>
														</li>
													{/each}
												</ol>
											</div>
										</details>
									{/if}
									{#if skillCalls.length > 0}
										<details class="rounded-xl border bg-[var(--canvas)]" style="border-color:var(--ds-border)" open>
											<summary class="flex cursor-pointer items-center gap-2 px-3 py-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
												<MessagesSquare class="size-3.5 text-emerald-400" />
												Skill calls ({skillCalls.length} call{skillCalls.length > 1 ? 's' : ''})
											</summary>
											<div class="border-t p-3" style="border-color:var(--ds-border)">
												<ol class="space-y-3">
													{#each skillCalls as call, idx (idx)}
														{@const parsedArgs = parseMaybeJson(call.arguments)}
														{@const httpStatus = extractHttpStatus(call.output)}
														{@const httpData = extractHttpData(call.output)}
														{@const outputBytes = approxBytes(call.output)}
														<li class="overflow-hidden rounded-xl border bg-[var(--canvas)]" style="border-color:var(--ds-border)">
															<header class="flex flex-wrap items-center justify-between gap-2 border-b px-3 py-2" style="border-color:var(--ds-border);background:var(--surface-hover)">
																<div class="flex items-center gap-2 min-w-0">
																	<span class="flex size-6 shrink-0 items-center justify-center rounded-md" style="background:color-mix(in srgb,#10b981 15%,transparent);border:1px solid color-mix(in srgb,#10b981 30%,transparent)">
																		<MessagesSquare class="size-3 text-emerald-400" />
																	</span>
																	<span class="font-mono text-xs font-semibold text-emerald-400 truncate">{call.name ?? '(unnamed)'}</span>
																</div>
																<div class="flex items-center gap-1.5">
																	{#if httpStatus !== null}
																		<span class="rounded px-1.5 py-0.5 font-mono text-[10px] {statusBadgeClass(httpStatus)}">HTTP {httpStatus}</span>
																	{/if}
																	{#if outputBytes > 0}
																		<span class="rounded bg-zinc-500/10 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">{fmtBytes(outputBytes)}</span>
																	{/if}
																	{#if call.iteration != null}
																		<span class="rounded bg-zinc-500/10 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">iter {call.iteration}</span>
																	{/if}
																</div>
															</header>
															<div class="space-y-3 p-3">
																<div>
																	<p class="mb-1 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase">Arguments</p>
																	{#if isEmptyArgs(parsedArgs)}
																		<p class="text-[11px] text-muted-foreground/60 italic">(no arguments)</p>
																	{:else}
																		<pre class="overflow-x-auto rounded-md bg-zinc-500/5 p-2 font-mono text-[11px] leading-relaxed text-foreground/80">{fmtJson(parsedArgs)}</pre>
																	{/if}
																</div>
																{#if call.error}
																	<div>
																		<p class="mb-1 text-[10px] font-semibold tracking-wider text-red-400 uppercase">Error</p>
																		<p class="rounded-md bg-red-500/5 p-2 text-[11px] text-red-400">{call.error}</p>
																	</div>
																{:else if call.output !== undefined && call.output !== null}
																	<details class="group" open={outputBytes < 2000}>
																		<summary class="mb-1 flex cursor-pointer items-center justify-between text-[10px] font-semibold tracking-wider text-muted-foreground uppercase">
																			<span>Output</span>
																			<span class="text-muted-foreground/60 normal-case">click to toggle</span>
																		</summary>
																		<pre class="max-h-[400px] overflow-auto rounded-md bg-zinc-500/5 p-2 font-mono text-[11px] leading-relaxed text-foreground/80">{fmtJson(httpData)}</pre>
																	</details>
																{/if}
															</div>
														</li>
													{/each}
												</ol>
											</div>
										</details>
									{/if}
									{#if trace.retrieved_chunks.length > 0 || trace.rag_error || trace.rag_scope.length > 0}
										<details class="rounded-xl border bg-[var(--canvas)]" style="border-color:var(--ds-border)" open>
											<summary class="flex cursor-pointer items-center gap-2 px-3 py-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
												<Database class="size-3.5 text-blue-400" />
												RAG · {trace.retrieved_chunks.length} chunk{trace.retrieved_chunks.length !== 1 ? 's' : ''}{#if trace.rag_error} · error{/if}
											</summary>
											<div class="border-t p-3" style="border-color:var(--ds-border)">
												{#if trace.rag_error}
													<p class="mb-3 rounded-xl border bg-red-500/5 p-4 text-xs text-red-400" style="border-color:color-mix(in srgb, var(--ds-border) 50%, #ef4444 50%)">
														<strong>Retrieval error:</strong> {trace.rag_error}
													</p>
												{/if}
												{#if trace.retrieved_chunks.length === 0}
													{#if trace.rag_scope.length === 0}
														<p class="rounded-xl border bg-zinc-500/5 p-4 text-xs text-muted-foreground" style="border-color:var(--ds-border)">Instance has no RAG scope. Configure collections in <code class="font-mono">rag_scope</code>.</p>
													{:else}
														<p class="rounded-xl border bg-amber-500/5 p-4 text-xs text-amber-300" style="border-color:color-mix(in srgb, var(--ds-border) 50%, #f59e0b 50%)">No chunks above the similarity threshold (<code class="font-mono">RAG_SCORE_THRESHOLD</code>). The query may need rewording, or the threshold may be too restrictive.</p>
													{/if}
												{:else}
													<ol class="space-y-2">
														{#each trace.retrieved_chunks as chunk, idx (idx)}
															<li class="rounded-xl border bg-[var(--canvas)] p-3" style="border-color:var(--ds-border)">
																<div class="mb-1.5 flex items-center justify-between">
																	<span class="flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground">
																		<FileText class="size-3" />
																		{chunk.filename ?? chunk.source ?? `chunk #${idx + 1}`}
																	</span>
																	<span class="rounded bg-emerald-500/10 px-1.5 py-0.5 font-mono text-[10px] text-emerald-400">score {fmtScore(chunk.score)}</span>
																</div>
																<p class="text-xs leading-relaxed text-foreground/80">{chunk.text}</p>
															</li>
														{/each}
													</ol>
												{/if}
											</div>
										</details>
									{/if}
									{#if trace.handoff_target}
										<details class="rounded-xl border bg-[var(--canvas)]" style="border-color:var(--ds-border)">
											<summary class="flex cursor-pointer items-center gap-2 px-3 py-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
												<GitBranch class="size-3.5 text-amber-400" />
												Handoff · {trace.handoff_target}
											</summary>
											<div class="border-t p-3 space-y-2" style="border-color:var(--ds-border)">
												{#if trace.handoff_summary}
													<p class="rounded-xl border bg-amber-500/5 p-4 text-xs text-amber-300" style="border-color:color-mix(in srgb, var(--ds-border) 50%, #f59e0b 50%)">{trace.handoff_summary}</p>
												{/if}
												{#if trace.linked_agents.length > 0}
													<details class="rounded-xl border bg-[var(--canvas)]" style="border-color:var(--ds-border)">
														<summary class="cursor-pointer px-3 py-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">Linked agents ({trace.linked_agents.length})</summary>
														<pre class="border-t px-3 py-2 font-mono text-[11px] leading-relaxed" style="border-color:var(--ds-border)">{fmtJson(trace.linked_agents)}</pre>
													</details>
												{/if}
											</div>
										</details>
									{/if}
									{#if trace.available_tools.length > 0}
										<div
											class="rounded-xl border bg-[var(--canvas)] p-3"
											style="border-color:var(--ds-border)"
										>
											<p
												class="mb-1.5 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase"
											>
												Available Tools ({trace.available_tools.length})
											</p>
											<div class="flex flex-wrap gap-1">
												{#each trace.available_tools as tool}
													<span
														class="rounded bg-zinc-500/10 px-1.5 py-0.5 font-mono text-[10px] text-foreground/80"
														>{tool}</span
													>
												{/each}
											</div>
										</div>
									{/if}
									{#if trace.available_skills.length > 0}
										<div
											class="rounded-xl border bg-[var(--canvas)] p-3"
											style="border-color:var(--ds-border)"
										>
											<p
												class="mb-1.5 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase"
											>
												Available Skills ({trace.available_skills.length})
											</p>
											<div class="flex flex-wrap gap-1">
												{#each trace.available_skills as skill}
													<span
														class="rounded bg-emerald-500/10 px-1.5 py-0.5 font-mono text-[10px] text-emerald-400"
														>{skill}</span
													>
												{/each}
											</div>
										</div>
									{/if}
									{#if trace.rag_scope.length > 0}
										<div
											class="rounded-xl border bg-[var(--canvas)] p-3"
											style="border-color:var(--ds-border)"
										>
											<p
												class="mb-1.5 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase"
											>
												RAG Scope ({trace.rag_scope.length})
											</p>
											<div class="flex flex-wrap gap-1">
												{#each trace.rag_scope as scope}
													<span
														class="rounded bg-blue-500/10 px-1.5 py-0.5 font-mono text-[10px] text-blue-400"
														>{scope}</span
													>
												{/each}
											</div>
										</div>
									{/if}
									<p
										class="text-[11px] font-semibold tracking-wider text-muted-foreground uppercase"
									>
										System prompt sections
									</p>
									{#each trace.system_prompt_sections as section (section.label)}
										{#if section.content}
											<details
												class="rounded-xl border bg-[var(--canvas)]"
												style="border-color:var(--ds-border)"
												open
											>
												<summary
													class="cursor-pointer px-3 py-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase"
												>
													{section.label}
													<span class="ml-2 text-[10px] text-muted-foreground/70 normal-case">
														({section.content.length} chars)
													</span>
												</summary>
												<pre
													class="border-t px-3 py-2 font-mono text-[11px] leading-relaxed break-words whitespace-pre-wrap"
													style="border-color:var(--ds-border)">{section.content}</pre>
											</details>
										{/if}
									{/each}
									{#if trace.system_prompt}
										<details
											class="rounded-xl border bg-[var(--canvas)]"
											style="border-color:var(--ds-border)"
										>
											<summary
												class="cursor-pointer px-3 py-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase"
											>
												Full system prompt
												<span class="ml-2 text-[10px] text-muted-foreground/70 normal-case">
													({trace.system_prompt.length} chars)
												</span>
											</summary>
											<pre
												class="border-t px-3 py-2 font-mono text-[11px] leading-relaxed break-words whitespace-pre-wrap"
												style="border-color:var(--ds-border)">{trace.system_prompt}</pre>
										</details>
									{/if}
								</div>
							{:else if selectedNode === 'respond'}
								{@render detailHeader(
									'Final response',
									`${fmtMs(trace.duration_ms)} total execution time`,
									MessageSquare
								)}
								<div
									class="rounded-xl border bg-[var(--canvas)] p-4 text-sm leading-relaxed whitespace-pre-wrap"
									style="border-color:var(--ds-border)"
								>
									{trace.final_response || '—'}
								</div>
							{/if}
						</div>
					</div>

				{:else if listLoading}
					<div class="flex flex-1 items-center justify-center text-sm text-muted-foreground">
						<Spinner class="mr-2 size-4" />
						Loading messages…
					</div>
				{:else}
					<div class="flex flex-1 items-center justify-center px-6">
						<div
							class="max-w-md rounded-xl border bg-[var(--canvas)] p-6 text-center text-sm text-muted-foreground"
							style="border-color:var(--ds-border)"
						>
							<Bot class="mx-auto mb-3 size-8 text-muted-foreground" />
							<p>
								{isStaticMode
									? 'No traces in this session.'
									: 'No traces yet. Send a message in the Test Agent panel.'}
							</p>
						</div>
					</div>
				{/if}
			</div>
			</div>
		</div>

		{#if trace && metadata}
			<footer
				class="flex items-center gap-3 border-t px-4 py-1.5 text-[10px] text-muted-foreground/70 shrink-0"
				style="border-color:var(--ds-border);background:var(--surface)"
			>
				<span class="font-mono text-primary">#{metadata.run_id.slice(0, 8)}</span>
				<span class="opacity-40">·</span>
				<span class="text-primary">{fmtMs(trace.duration_ms)}</span>
				{#if trace.token_usage}
					<span class="opacity-40">·</span>
					<span class="font-mono text-blue-400" title="Prompt tokens">P {fmtTokens(trace.token_usage.prompt_tokens)}</span>
					<span class="opacity-40">/</span>
					<span class="font-mono text-emerald-400" title="Completion tokens">C {fmtTokens(trace.token_usage.completion_tokens)}</span>
					<span class="opacity-40">/</span>
					<span class="font-mono text-amber-400" title={`Embedding tokens across ${trace.token_usage.embedding_calls} call(s)`}>E {fmtTokens(trace.token_usage.embedding_tokens)}</span>
					<span class="opacity-40">/</span>
					<span class="font-mono text-purple-400" title="Total LLM and embedding tokens">T {fmtTokens(traceTrackedTokens(trace))}</span>
				{/if}
				<span class="opacity-40">·</span>
				<span class="text-primary">{trace.model ?? '?'}</span>
				<span class="opacity-40">·</span>
				<span class="text-primary">{trace.ai_provider ?? '?'}</span>
				<span class="opacity-40">·</span>
				<span class="text-primary">{new Date(metadata.created_at).toLocaleString('pt-BR')}</span>
			</footer>
		{/if}
	</div>
{/if}

<style>
	:global(.svelte-flow) {
		background: var(--canvas);
	}
	:global(.svelte-flow__node) {
		font-family: inherit;
		cursor: pointer;
		white-space: pre-line;
	}
	:global(.svelte-flow__attribution) {
		display: none;
	}
	:global(.svelte-flow__controls button) {
		background: var(--surface);
		border-color: var(--ds-border);
		color: var(--text-muted);
	}
	:global(.svelte-flow__controls button:hover) {
		background: var(--surface-hover);
	}
</style>
