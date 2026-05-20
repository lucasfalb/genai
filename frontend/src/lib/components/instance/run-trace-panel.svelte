<script lang="ts">
	import { untrack, type Component } from 'svelte';
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
	import { tracesApi } from '$lib/api/chat';
	import { chatSessionStore } from '$lib/stores/chat-session.svelte';
	import { authStore } from '$lib/stores/auth.svelte';
	import { tenantStore } from '$lib/stores/tenant.svelte';
	import { ApiError, getErrorMessage } from '$lib/api/client';
	import { renderFormattedMessage } from '$lib/utils/rich-message';
	import type {
		RunTracePayload,
		RunTraceResponse,
		RunTraceListItem,
		RunTraceExecutedCall,
		RunTraceTokenCall
	} from '$lib/api/types';

	let {
		instanceId,
		sessionId: propSessionId,
		runId: propRunId
	}: { instanceId: string; sessionId?: string | null; runId?: string | null } = $props();

	let loading = $state(false);
	let error = $state('');
	let trace = $state<RunTracePayload | null>(null);
	let metadata = $state<RunTraceResponse | null>(null);
	let selectedNodeId = $state<string | null>(null);

	let runs = $state<RunTraceListItem[]>([]);
	let selectedRunId = $state<string | null>(null);
	let listLoading = $state(false);

	const isStaticMode = $derived(propSessionId !== undefined && propSessionId !== null);

	const debSessId = $derived(chatSessionStore.sessionId(instanceId));
	const debRunId = $derived(chatSessionStore.lastRunId(instanceId));

	const liveSteps = $derived(chatSessionStore.liveNodeSteps(instanceId));
	const liveRunId = $derived(chatSessionStore.liveRunId(instanceId));
	const isLiveRunActive = $derived(liveRunId !== null);
	const authReady = $derived(Boolean(authStore.accessToken && tenantStore.activeTenantId));

	const reloadKey = $derived(
		!authReady
			? null
			: propRunId
				? `${instanceId}-${propRunId}`
				: isStaticMode
					? `${instanceId}-${propSessionId}`
					: `${instanceId}-${debSessId}-${debRunId}`
	);

	const sessionTotalTokens = $derived(runs.reduce((sum, r) => sum + listItemTrackedTokens(r), 0));

	$effect(() => {
		const key = reloadKey;
		if (!key) return;
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

	// ─── Utilities ────────────────────────────────────────────────────────────────

	function fmtMs(ms: number): string {
		return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(2)} s`;
	}

	function fmtScore(score?: number | null): string {
		return typeof score === 'number' ? score.toFixed(3) : '—';
	}

	function fmtJson(value: unknown): string {
		if (value == null) return '—';
		try {
			return JSON.stringify(value, null, 2);
		} catch {
			return String(value);
		}
	}

	function renderTraceMessage(value: unknown): string {
		if (value == null) return renderFormattedMessage('—');
		return renderFormattedMessage(typeof value === 'string' ? value : fmtJson(value));
	}

	function parseMaybeJson(value: unknown): unknown {
		if (typeof value !== 'string') return value;
		const t = value.trim();
		if (!t || (t[0] !== '{' && t[0] !== '[' && t[0] !== '"')) return value;
		try {
			return JSON.parse(t);
		} catch {
			return value;
		}
	}

	function isEmptyArgs(value: unknown): boolean {
		if (value == null) return true;
		if (typeof value === 'object' && !Array.isArray(value))
			return Object.keys(value as Record<string, unknown>).length === 0;
		return false;
	}

	function extractHttpStatus(output: unknown): number | null {
		const p = parseMaybeJson(output) as { status?: unknown } | null;
		return p && typeof p === 'object' && typeof p.status === 'number' ? p.status : null;
	}

	function extractHttpData(output: unknown): unknown {
		const p = parseMaybeJson(output);
		return p && typeof p === 'object' && p !== null && 'data' in p
			? (p as { data: unknown }).data
			: p;
	}

	function statusBadgeClass(status: number | null): string {
		if (status === null) return 'bg-zinc-500/10 text-muted-foreground';
		if (status >= 200 && status < 300) return 'bg-emerald-500/10 text-emerald-400';
		if (status >= 300 && status < 400) return 'bg-blue-500/10 text-blue-400';
		if (status >= 400 && status < 500) return 'bg-amber-500/10 text-amber-400';
		return 'bg-red-500/10 text-red-400';
	}

	function approxBytes(value: unknown): number {
		if (value == null) return 0;
		try {
			return typeof value === 'string' ? value.length : JSON.stringify(value).length;
		} catch {
			return 0;
		}
	}

	function fmtBytes(n: number): string {
		if (n < 1024) return `${n} B`;
		if (n < 1048576) return `${(n / 1024).toFixed(1)} KB`;
		return `${(n / 1048576).toFixed(1)} MB`;
	}

	function listItemTrackedTokens(run: RunTraceListItem): number {
		return (run.total_tokens ?? 0) + (run.embedding_tokens ?? 0);
	}

	function traceTrackedTokens(t: RunTracePayload): number {
		return t.token_usage
			? (t.token_usage.total_tokens ?? 0) + (t.token_usage.embedding_tokens ?? 0)
			: 0;
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
		return n < 1000 ? String(n) : `${(n / 1000).toFixed(1)}k`;
	}

	function fmtTime(value: string): string {
		return new Date(value).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
	}

	function stepTriggerLabel(triggers: string[] | null | undefined): string {
		if (!triggers?.length) return '';
		return triggers.map((t) => t.replace(/__/g, '')).join(', ');
	}

	// ─── Step-iteration correlation ───────────────────────────────────────────────
	// LangGraph iteration mapping:
	//   llm_node reads tool_call_iterations (0-based) → per_call[N].iteration === N
	//   dispatch_node increments to N+1 → executed_tool_calls[*].iteration === N+1
	//
	// So: LLM step at position N in sorted llm steps → per_call[N] → tool calls with iteration N+1

	function llmIterationForStep(stepNum: number | null): number {
		if (stepNum == null || !trace) return -1;
		const sorted = (trace.node_timings ?? [])
			.filter((n) => n.name === 'llm')
			.sort((a, b) => (a.step ?? 0) - (b.step ?? 0));
		return sorted.findIndex((n) => n.step === stepNum);
	}

	function dispatchIterationForStep(stepNum: number | null): number {
		// Returns 1-based iteration matching executed_tool_calls.iteration
		if (stepNum == null || !trace) return -1;
		const sorted = (trace.node_timings ?? [])
			.filter((n) => n.name === 'dispatch')
			.sort((a, b) => (a.step ?? 0) - (b.step ?? 0));
		const idx = sorted.findIndex((n) => n.step === stepNum);
		return idx >= 0 ? idx + 1 : -1;
	}

	function toolCallsForDispatchStep(stepNum: number | null): RunTraceExecutedCall[] {
		const iter = dispatchIterationForStep(stepNum);
		if (iter < 1) return executedCalls;
		return executedCalls.filter((c) => c.iteration === iter);
	}

	function perCallForLlmStep(stepNum: number | null): RunTraceTokenCall | null {
		if (!trace?.token_usage) return null;
		const iter = llmIterationForStep(stepNum);
		if (iter < 0) return null;
		return trace.token_usage.per_call.find((c) => c.iteration === iter) ?? null;
	}

	function toolDecisionsForLlmStep(stepNum: number | null): RunTraceExecutedCall[] {
		// Tools that this LLM iteration decided to call → dispatched in the next dispatch node
		const llmIter = llmIterationForStep(stepNum);
		if (llmIter < 0) return [];
		return executedCalls.filter((c) => c.iteration === llmIter + 1);
	}

	function nodeTextColor(name: string): string {
		const colors: Record<string, string> = {
			rag: '#93c5fd',
			llm: '#86efac',
			dispatch: '#fde68a',
			handoff: '#fdba74',
			__input__: '#d6d3d1',
			__output__: '#86efac'
		};
		return colors[name] ?? '#d4d4d8';
	}

	function tokenHotspots(t: RunTracePayload): {
		key: string | null;
		title: string;
		subtitle: string;
		promptTokens: number;
		totalTokens: number;
	}[] {
		const llmSteps = (t.node_timings ?? [])
			.map((step, idx) => ({ ...step, idx }))
			.filter((step) => step.name === 'llm')
			.sort((a, b) => (a.step ?? 0) - (b.step ?? 0));
		return (t.token_usage?.per_call ?? [])
			.map((call, idx) => {
				const iteration = call.iteration ?? idx;
				const step = llmSteps[iteration];
				return {
					key: step ? `${step.name}-${step.step ?? step.idx}` : null,
					title: `LLM #${step?.step ?? iteration}`,
					subtitle: `${call.phase === 'final' ? 'final response' : 'tool decision'} · ${fmtTokens(call.completion_tokens)} completion`,
					promptTokens: call.prompt_tokens,
					totalTokens: call.total_tokens
				};
			})
			.sort((a, b) => b.promptTokens - a.promptTokens)
			.slice(0, 4);
	}

	// ─── Flow graph ───────────────────────────────────────────────────────────────

	type FlowStep = {
		key: string;
		name: string;
		step: number | null;
		status: 'running' | 'completed' | 'error';
		duration_ms?: number;
		error?: string | null;
		triggers?: string[] | null;
		started_at?: string | null;
		ended_at?: string | null;
	};

	const activeFlowSteps = $derived.by((): FlowStep[] => {
		if (isLiveRunActive && liveSteps.length > 0) {
			return liveSteps.map((s, idx) => ({
				key: `live-${s.name}-${s.step ?? idx}`,
				name: s.name,
				step: s.step,
				status: s.status as 'running' | 'completed' | 'error',
				duration_ms: s.duration_ms,
				error: s.error,
				triggers: s.triggers
			}));
		}
		const t = trace;
		if (!t) return [];
		const steps: FlowStep[] = [
			{ key: '__input__', name: '__input__', step: null, status: 'completed' }
		];
		for (const [idx, n] of (t.node_timings ?? []).entries()) {
			steps.push({
				key: `step-${idx}`,
				name: n.name,
				step: n.step,
				status: n.error ? 'error' : 'completed',
				duration_ms: n.duration_ms,
				error: n.error,
				triggers: n.triggers,
				started_at: n.started_at,
				ended_at: n.ended_at
			});
		}
		if ((t.node_timings ?? []).length > 0) {
			steps.push({
				key: '__output__',
				name: '__output__',
				step: null,
				status: 'completed',
				duration_ms: t.duration_ms
			});
		}
		return steps;
	});

	const selectedStep = $derived(
		selectedNodeId != null ? (activeFlowSteps.find((s) => s.key === selectedNodeId) ?? null) : null
	);

	const executedCalls = $derived.by(() => {
		const t = trace;
		if (!t) return [] as RunTraceExecutedCall[];
		const list = t.executed_tool_calls ?? [];
		if (list.length > 0) return list;
		const availableSkills = new Set(t.available_skills ?? []);
		const pendingByName = new Map<string, (typeof t.pending_tool_calls)[number]>();
		for (const p of t.pending_tool_calls ?? []) {
			if (p.name) pendingByName.set(p.name, p);
		}
		return (t.tool_results ?? []).map((r) => {
			const name = r.name ?? '';
			return {
				id: r.id ?? null,
				name,
				kind: (availableSkills.has(name) ? 'skill' : 'tool') as 'skill' | 'tool',
				arguments: pendingByName.get(name)?.arguments ?? null,
				output: r.output,
				error: r.error,
				iteration: null
			};
		});
	});
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
			onclick={() => (selectedNodeId = null)}
			class="rounded-md p-1 text-muted-foreground transition-colors hover:bg-[var(--surface-hover)] hover:text-foreground"
			aria-label="Close details"
		>
			<X class="size-3.5" />
		</button>
	</div>
{/snippet}

<style>
	.rich-trace-message {
		white-space: normal;
	}
	.rich-trace-message :global(p) {
		margin: 0 0 0.72em;
	}
	.rich-trace-message :global(p:last-child),
	.rich-trace-message :global(ul:last-child),
	.rich-trace-message :global(h3:last-child),
	.rich-trace-message :global(h4:last-child) {
		margin-bottom: 0;
	}
	.rich-trace-message :global(ul) {
		margin: 0.35em 0 0.8em;
		padding-left: 1.2em;
	}
	.rich-trace-message :global(li) {
		margin: 0.22em 0;
		padding-left: 0.1em;
	}
	.rich-trace-message :global(strong) {
		font-weight: 750;
		color: color-mix(in srgb, currentColor 88%, #fff 12%);
	}
	.rich-trace-message :global(code) {
		border-radius: 6px;
		background: rgba(148, 163, 184, 0.14);
		padding: 0.1em 0.34em;
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 0.92em;
	}
	.rich-trace-message :global(a) {
		color: inherit;
		font-weight: 700;
		text-decoration: underline;
		text-underline-offset: 2px;
	}
	.rich-trace-message :global(h3),
	.rich-trace-message :global(h4) {
		margin: 0.1em 0 0.45em;
		font-size: 1em;
		line-height: 1.35;
		font-weight: 800;
	}
</style>

{#snippet toolCallList(calls: RunTraceExecutedCall[])}
	<ol class="space-y-3">
		{#each calls as call, idx (idx)}
			{@const parsedArgs = parseMaybeJson(call.arguments)}
			{@const httpStatus = extractHttpStatus(call.output)}
			{@const httpData = extractHttpData(call.output)}
			{@const outputBytes = approxBytes(call.output)}
			<li class="overflow-hidden rounded-xl border" style="border-color:var(--ds-border)">
				<header
					class="flex flex-wrap items-center justify-between gap-2 border-b px-3 py-2"
					style="border-color:var(--ds-border);background:var(--surface-hover)"
				>
					<div class="flex min-w-0 items-center gap-2">
						<span
							class="flex size-6 shrink-0 items-center justify-center rounded-md"
							style={call.kind === 'skill'
								? 'background:color-mix(in srgb,#10b981 15%,transparent);border:1px solid color-mix(in srgb,#10b981 30%,transparent)'
								: 'background:color-mix(in srgb,#3b82f6 15%,transparent);border:1px solid color-mix(in srgb,#3b82f6 30%,transparent)'}
						>
							{#if call.kind === 'skill'}
								<MessagesSquare class="size-3 text-emerald-400" />
							{:else}
								<Wrench class="size-3 text-blue-400" />
							{/if}
						</span>
						<span
							class="truncate font-mono text-xs font-semibold {call.kind === 'skill'
								? 'text-emerald-400'
								: 'text-blue-400'}">{call.name ?? '(unnamed)'}</span
						>
						<span
							class="rounded px-1.5 py-0.5 text-[9px] font-semibold tracking-wider uppercase {call.kind ===
							'skill'
								? 'bg-emerald-500/10 text-emerald-400'
								: 'bg-blue-500/10 text-blue-400'}">{call.kind}</span
						>
					</div>
					<div class="flex items-center gap-1.5">
						{#if httpStatus !== null}
							<span
								class="rounded px-1.5 py-0.5 font-mono text-[10px] {statusBadgeClass(httpStatus)}"
								>HTTP {httpStatus}</span
							>
						{/if}
						{#if outputBytes > 0}
							<span
								class="rounded bg-zinc-500/10 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
								>{fmtBytes(outputBytes)}</span
							>
						{/if}
					</div>
				</header>
				<div class="space-y-3 p-3">
					<div>
						<p
							class="mb-1 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase"
						>
							Arguments
						</p>
						{#if isEmptyArgs(parsedArgs)}
							<p class="text-[11px] text-muted-foreground/60 italic">(no arguments)</p>
						{:else}
							<pre
								class="overflow-x-auto rounded-md bg-zinc-500/5 p-2 font-mono text-[11px] leading-relaxed text-foreground/80">{fmtJson(
									parsedArgs
								)}</pre>
						{/if}
					</div>
					{#if call.error}
						<div>
							<p class="mb-1 text-[10px] font-semibold tracking-wider text-red-400 uppercase">
								Error
							</p>
							<p class="rounded-md bg-red-500/5 p-2 text-[11px] text-red-400">{call.error}</p>
						</div>
					{:else if call.output !== undefined && call.output !== null}
						<details open={outputBytes < 2000}>
							<summary
								class="mb-1 flex cursor-pointer items-center justify-between text-[10px] font-semibold tracking-wider text-muted-foreground uppercase"
							>
								<span>Output</span>
								<span class="text-muted-foreground/60 normal-case">click to toggle</span>
							</summary>
							<pre
								class="max-h-96 overflow-auto rounded-md bg-zinc-500/5 p-2 font-mono text-[11px] leading-relaxed text-foreground/80">{fmtJson(
									httpData
								)}</pre>
						</details>
					{/if}
				</div>
			</li>
		{/each}
	</ol>
{/snippet}

{#snippet promptContextPanel()}
	{#if trace}
		<section class="mt-4 space-y-3">
			<p class="text-[10px] font-semibold tracking-wider text-muted-foreground uppercase">
				Prompt &amp; Context
			</p>

			<details class="rounded-xl border bg-[var(--canvas)]" style="border-color:var(--ds-border)">
				<summary
					class="cursor-pointer px-3 py-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase"
				>
					Full system prompt
					<span class="ml-2 text-[10px] text-muted-foreground/70 normal-case">
						({trace.system_prompt?.length ?? 0} chars)
					</span>
				</summary>
				<pre
					class="max-h-96 overflow-auto border-t px-3 py-2 font-mono text-[11px] leading-relaxed break-words whitespace-pre-wrap"
					style="border-color:var(--ds-border)">{trace.system_prompt || '—'}</pre>
			</details>

			{#if trace.system_prompt_sections.length > 0}
				<details class="rounded-xl border bg-[var(--canvas)]" style="border-color:var(--ds-border)">
					<summary
						class="cursor-pointer px-3 py-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase"
					>
						Prompt sections ({trace.system_prompt_sections.filter((s) => s.content).length})
					</summary>
					<div class="space-y-2 border-t p-3" style="border-color:var(--ds-border)">
						{#each trace.system_prompt_sections.filter((s) => s.content) as section (section.label)}
							<details
								class="rounded-lg border bg-zinc-500/5"
								style="border-color:var(--ds-border)"
							>
								<summary
									class="cursor-pointer px-2.5 py-2 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase"
								>
									{section.label}
									<span class="ml-1 text-muted-foreground/60 normal-case">
										({section.content.length} chars)
									</span>
								</summary>
								<pre
									class="max-h-72 overflow-auto border-t px-2.5 py-2 font-mono text-[11px] leading-relaxed break-words whitespace-pre-wrap"
									style="border-color:var(--ds-border)">{section.content}</pre>
							</details>
						{/each}
					</div>
				</details>
			{/if}

			<details class="rounded-xl border bg-[var(--canvas)]" style="border-color:var(--ds-border)">
				<summary
					class="cursor-pointer px-3 py-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase"
				>
					Messages sent to LLM
					<span class="ml-2 text-[10px] text-muted-foreground/70 normal-case">
						({trace.messages?.length ?? 0})
					</span>
				</summary>
				{#if trace.messages?.length}
					<ol class="space-y-2 border-t p-3" style="border-color:var(--ds-border)">
						{#each trace.messages as message, idx (idx)}
							<li
								class="rounded-lg border bg-zinc-500/5 p-2.5"
								style="border-color:var(--ds-border)"
							>
								<div class="mb-1.5 flex items-center justify-between gap-2">
									<span
										class="rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold {message.role ===
										'user'
											? 'bg-blue-500/10 text-blue-400'
											: message.role === 'assistant'
												? 'bg-emerald-500/10 text-emerald-400'
												: message.role === 'tool'
													? 'bg-amber-500/10 text-amber-400'
													: 'bg-zinc-500/10 text-muted-foreground'}">{message.role}</span
									>
									<span class="font-mono text-[10px] text-muted-foreground/60">#{idx + 1}</span>
								</div>
								{#if message.tool_calls}
									<pre
										class="mb-2 max-h-48 overflow-auto rounded bg-black/10 p-2 font-mono text-[10px] leading-relaxed text-foreground/80">{fmtJson(
											message.tool_calls
										)}</pre>
								{/if}
								{#if message.tool_call_id}
									<p class="mb-1 font-mono text-[10px] text-muted-foreground">
										tool_call_id: {message.tool_call_id}
									</p>
								{/if}
								{#if typeof message.content === 'string' || message.content == null}
									<div
										class="rich-trace-message max-h-72 overflow-auto rounded bg-black/10 p-2 text-[12px] leading-relaxed break-words text-foreground/85"
									>
										{@html renderTraceMessage(message.content)}
									</div>
								{:else}
									<pre
										class="max-h-72 overflow-auto rounded bg-black/10 p-2 font-mono text-[11px] leading-relaxed break-words whitespace-pre-wrap text-foreground/80">{fmtJson(
											message.content
										)}</pre>
								{/if}
							</li>
						{/each}
					</ol>
				{:else}
					<p
						class="border-t px-3 py-2 text-xs text-muted-foreground"
						style="border-color:var(--ds-border)"
					>
						This run was captured before message context tracing was added.
					</p>
				{/if}
			</details>

			<details class="rounded-xl border bg-[var(--canvas)]" style="border-color:var(--ds-border)">
				<summary
					class="cursor-pointer px-3 py-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase"
				>
					Thinking / reasoning
				</summary>
				<div
					class="border-t p-3 text-xs text-muted-foreground"
					style="border-color:var(--ds-border)"
				>
					{#if trace.thinking || trace.reasoning}
						<pre class="font-mono text-[11px] leading-relaxed whitespace-pre-wrap">{fmtJson(
								trace.thinking ?? trace.reasoning
							)}</pre>
					{:else}
						<p>
							No thinking/reasoning content was exposed by this provider call. The current
							OpenAI-compatible chat stream records token usage and tool decisions, but not hidden
							model reasoning.
						</p>
					{/if}
				</div>
			</details>

			{#if trace.tool_schemas.length > 0 || trace.available_tools.length > 0 || trace.available_skills.length > 0}
				<details class="rounded-xl border bg-[var(--canvas)]" style="border-color:var(--ds-border)">
					<summary
						class="cursor-pointer px-3 py-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase"
					>
						Available tools &amp; schemas
					</summary>
					<div class="space-y-3 border-t p-3" style="border-color:var(--ds-border)">
						{#if trace.available_tools.length > 0 || trace.available_skills.length > 0}
							<div class="flex flex-wrap gap-1.5">
								{#each trace.available_tools as tool}
									<span
										class="rounded bg-blue-500/10 px-1.5 py-0.5 font-mono text-[10px] text-blue-400"
										>{tool}</span
									>
								{/each}
								{#each trace.available_skills as skill}
									<span
										class="rounded bg-emerald-500/10 px-1.5 py-0.5 font-mono text-[10px] text-emerald-400"
										>{skill}</span
									>
								{/each}
							</div>
						{/if}
						{#if trace.tool_schemas.length > 0}
							<pre
								class="max-h-96 overflow-auto rounded bg-black/10 p-2 font-mono text-[11px] leading-relaxed text-foreground/80">{fmtJson(
									trace.tool_schemas
								)}</pre>
						{/if}
					</div>
				</details>
			{/if}
		</section>
	{/if}
{/snippet}

{#snippet runOverview()}
	{#if trace}
		<div class="space-y-5">
			<div class="flex items-start justify-between gap-3">
				<div>
					<p class="text-[10px] font-semibold tracking-wider text-muted-foreground uppercase">
						Run Overview
					</p>
					<h3 class="mt-1 text-sm font-semibold" style="color:var(--text-main)">
						{trace.model ?? '?'} · {trace.ai_provider ?? '?'}
					</h3>
					<p class="mt-1 text-xs text-muted-foreground">
						Select a step from the timeline to inspect details.
					</p>
				</div>
				<span class="shrink-0 font-mono text-xs text-muted-foreground"
					>{fmtMs(trace.duration_ms)}</span
				>
			</div>

			<div class="grid grid-cols-2 gap-2 xl:grid-cols-4">
				<div class="rounded-xl border bg-[var(--canvas)] p-3" style="border-color:var(--ds-border)">
					<p class="text-[10px] tracking-wider text-muted-foreground uppercase">Steps</p>
					<p class="mt-1 font-mono text-lg font-semibold text-blue-400">
						{trace.node_timings.length}
					</p>
				</div>
				<div class="rounded-xl border bg-[var(--canvas)] p-3" style="border-color:var(--ds-border)">
					<p class="text-[10px] tracking-wider text-muted-foreground uppercase">Prompt</p>
					<p class="mt-1 font-mono text-lg font-semibold text-blue-400">
						{fmtTokens(trace.token_usage?.prompt_tokens)}
					</p>
				</div>
				<div class="rounded-xl border bg-[var(--canvas)] p-3" style="border-color:var(--ds-border)">
					<p class="text-[10px] tracking-wider text-muted-foreground uppercase">Completion</p>
					<p class="mt-1 font-mono text-lg font-semibold text-emerald-400">
						{fmtTokens(trace.token_usage?.completion_tokens)}
					</p>
				</div>
				<div class="rounded-xl border bg-[var(--canvas)] p-3" style="border-color:var(--ds-border)">
					<p class="text-[10px] tracking-wider text-muted-foreground uppercase">Tools</p>
					<p class="mt-1 font-mono text-lg font-semibold text-amber-300">
						{executedCalls.length}
					</p>
				</div>
			</div>

			<div class="grid gap-3 xl:grid-cols-2">
				<section
					class="rounded-xl border bg-[var(--canvas)] p-3"
					style="border-color:var(--ds-border)"
				>
					<div class="mb-2 flex items-center justify-between gap-2">
						<p class="text-[10px] font-semibold tracking-wider text-muted-foreground uppercase">
							Cost hotspots
						</p>
						<span class="font-mono text-[10px] text-purple-400"
							>{fmtTokens(traceTrackedTokens(trace))} total</span
						>
					</div>
					{#if tokenHotspots(trace).length > 0}
						<div class="space-y-1.5">
							{#each tokenHotspots(trace) as hotspot}
								<button
									type="button"
									class="w-full rounded-lg border px-2.5 py-2 text-left transition-colors hover:border-blue-500/30 hover:bg-[var(--surface-hover)]"
									style="border-color:var(--ds-border)"
									onclick={() => {
										if (hotspot.key) selectedNodeId = hotspot.key;
									}}
								>
									<div class="flex items-center justify-between gap-2">
										<span class="font-mono text-[11px] font-semibold text-emerald-400">
											{hotspot.title}
										</span>
										<span class="font-mono text-[11px] text-blue-400">
											{fmtTokens(hotspot.promptTokens)} prompt
										</span>
									</div>
									<p class="mt-0.5 truncate text-[10px] text-muted-foreground">
										{hotspot.subtitle} · {fmtTokens(hotspot.totalTokens)} total
									</p>
								</button>
							{/each}
						</div>
					{:else}
						<p class="text-xs text-muted-foreground">No per-call token usage was recorded.</p>
					{/if}
				</section>

				<section
					class="rounded-xl border bg-[var(--canvas)] p-3"
					style="border-color:var(--ds-border)"
				>
					<p class="mb-2 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase">
						Execution summary
					</p>
					<dl class="space-y-2 text-xs">
						<div class="flex justify-between gap-3">
							<dt class="text-muted-foreground">LLM calls</dt>
							<dd class="font-mono text-emerald-400">{trace.token_usage?.llm_calls ?? 0}</dd>
						</div>
						<div class="flex justify-between gap-3">
							<dt class="text-muted-foreground">RAG chunks</dt>
							<dd class="font-mono text-blue-400">{trace.retrieved_chunks.length}</dd>
						</div>
						<div class="flex justify-between gap-3">
							<dt class="text-muted-foreground">Messages in context</dt>
							<dd class="font-mono text-purple-400">{trace.messages?.length ?? 0}</dd>
						</div>
						<div class="flex justify-between gap-3">
							<dt class="text-muted-foreground">Tool output stored</dt>
							<dd class="font-mono text-amber-300">
								{fmtBytes(approxBytes(trace.executed_tool_calls))}
							</dd>
						</div>
					</dl>
				</section>
			</div>

			{@render promptContextPanel()}
		</div>
	{:else if isLiveRunActive}
		<div class="space-y-4">
			<div>
				<p class="text-[10px] font-semibold tracking-wider text-muted-foreground uppercase">
					Live Run
				</p>
				<h3 class="mt-1 text-sm font-semibold" style="color:var(--text-main)">
					Execution in progress
				</h3>
				<p class="mt-1 text-xs text-muted-foreground">
					Select a running step from the timeline to inspect its live status.
				</p>
			</div>
			<div class="rounded-xl border bg-[var(--canvas)] p-3" style="border-color:var(--ds-border)">
				<div class="flex items-center justify-between">
					<span class="text-xs text-muted-foreground">Completed steps</span>
					<span class="font-mono text-xs text-emerald-400">
						{liveSteps.filter((s) => s.status === 'completed').length}/{liveSteps.length}
					</span>
				</div>
				{#if liveSteps.find((s) => s.status === 'running')}
					{@const running = liveSteps.find((s) => s.status === 'running')}
					<div class="mt-3 flex items-center gap-2 text-xs text-emerald-400">
						<Spinner class="size-3" />
						<span>{running?.name} is running</span>
					</div>
				{/if}
			</div>
		</div>
	{/if}
{/snippet}

{#snippet executionTimeline()}
	{#if isLiveRunActive}
		<div class="space-y-2 p-4">
			<p class="mb-3 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase">
				Live Execution
			</p>
			{#if liveSteps.length === 0}
				<div class="flex items-center gap-2 text-xs text-muted-foreground">
					<Spinner class="size-3" />
					<span>Starting execution…</span>
				</div>
			{:else}
				{#each liveSteps as step}
					<div
						class="flex items-center gap-2 rounded-xl border px-3 py-2"
						style="border-color:var(--ds-border);background:var(--canvas)"
					>
						<span
							class="font-mono text-[11px] font-semibold"
							style="color:{nodeTextColor(step.name)}">{step.name}</span
						>
						{#if step.step != null}
							<span class="font-mono text-[10px] text-muted-foreground/50">step {step.step}</span>
						{/if}
						<span class="ml-auto">
							{#if step.status === 'running'}
								<span class="flex items-center gap-1 text-[10px] text-amber-400">
									<Spinner class="size-2.5" />
									running…
								</span>
							{:else if step.status === 'error'}
								<span class="text-[10px] text-red-400">error</span>
							{:else}
								<span class="font-mono text-[10px] text-emerald-400">
									{step.duration_ms != null ? fmtMs(step.duration_ms) : 'done'}
								</span>
							{/if}
						</span>
					</div>
				{/each}
			{/if}
		</div>
	{:else if trace && (trace.user_message || (trace.node_timings ?? []).length > 0)}
		<div class="space-y-1.5 p-4">
			<div class="mb-3 flex items-center justify-between">
				<p class="text-[10px] font-semibold tracking-wider text-muted-foreground uppercase">
					Execution Timeline · {(trace.node_timings ?? []).length +
						(trace.user_message ? 1 : 0) +
						(trace.final_response ? 1 : 0)} steps
				</p>
				<span class="font-mono text-[11px] text-muted-foreground">{fmtMs(trace.duration_ms)}</span>
			</div>

			{#if trace.user_message}
				<button
					type="button"
					onclick={() => (selectedNodeId = selectedNodeId === '__input__' ? null : '__input__')}
					class="w-full overflow-hidden rounded-xl border text-left transition-colors hover:border-blue-500/30 {selectedNodeId ===
					'__input__'
						? 'border-blue-500/40'
						: ''}"
					style="border-color:{selectedNodeId === '__input__' ? '' : 'var(--ds-border)'}"
				>
					<div
						class="flex items-center gap-2 px-3 py-2.5"
						style="background:{selectedNodeId === '__input__'
							? 'color-mix(in srgb,#3b82f6 8%,transparent)'
							: 'var(--canvas)'}"
					>
						<span class="w-5 shrink-0 text-center font-mono text-[10px] text-muted-foreground/50"
							>↗</span
						>
						<span
							class="font-mono text-[11px] font-semibold"
							style="color:{nodeTextColor('__input__')}">user</span
						>
						<span class="ml-2 min-w-0 flex-1 truncate text-[10px] text-muted-foreground/60 italic">
							{trace.user_message.length > 28
								? trace.user_message.slice(0, 28) + '…'
								: trace.user_message}
						</span>
					</div>
				</button>
			{/if}

			{#each trace.node_timings as step, idx (idx)}
				{@const llmIter = step.name === 'llm' ? llmIterationForStep(step.step) : -1}
				{@const perCall =
					llmIter >= 0
						? (trace.token_usage?.per_call?.find((c) => c.iteration === llmIter) ?? null)
						: null}
				{@const decisions = step.name === 'llm' ? toolDecisionsForLlmStep(step.step) : []}
				{@const dispatchCalls = step.name === 'dispatch' ? toolCallsForDispatchStep(step.step) : []}
				{@const stepKey = `step-${idx}`}

				<button
					type="button"
					onclick={() => (selectedNodeId = selectedNodeId === stepKey ? null : stepKey)}
					class="w-full overflow-hidden rounded-xl border text-left transition-colors hover:border-blue-500/30 {selectedNodeId ===
					stepKey
						? 'border-blue-500/40'
						: ''}"
					style="border-color:{selectedNodeId === stepKey ? '' : 'var(--ds-border)'}"
				>
					<!-- Step header -->
					<div
						class="flex items-center gap-2 px-3 py-2"
						style="background:{selectedNodeId === stepKey
							? 'color-mix(in srgb,#3b82f6 8%,transparent)'
							: 'var(--canvas)'}"
					>
						<span class="w-5 shrink-0 text-center font-mono text-[10px] text-muted-foreground/50"
							>{idx + 1}</span
						>
						<span
							class="font-mono text-[11px] font-semibold"
							style="color:{nodeTextColor(step.name)}">{step.name}</span
						>
						{#if step.triggers?.length}
							<span class="text-[9px] text-muted-foreground/50">
								← {stepTriggerLabel(step.triggers)}
							</span>
						{/if}
						<span
							class="ml-auto shrink-0 font-mono text-[10px] {step.error
								? 'text-red-400'
								: 'text-muted-foreground/60'}"
						>
							{step.error ? 'error' : fmtMs(step.duration_ms)}
						</span>
					</div>

					<!-- RAG sub-row -->
					{#if step.name === 'rag'}
						<div
							class="border-t px-3 py-1.5 text-[10px] text-muted-foreground"
							style="border-color:var(--ds-border)"
						>
							{#if trace.rag_error}
								<span class="text-red-400">Retrieval error: {trace.rag_error}</span>
							{:else if trace.retrieved_chunks.length > 0}
								{trace.retrieved_chunks.length} chunk{trace.retrieved_chunks.length !== 1
									? 's'
									: ''} retrieved
								{#if trace.rag_scope.length > 0}
									from {trace.rag_scope.join(', ')}
								{/if}
							{:else if trace.rag_scope.length > 0}
								<span class="text-amber-400">No results above threshold</span>
							{:else}
								<span class="opacity-60">No RAG scope configured</span>
							{/if}
						</div>
					{/if}

					<!-- LLM sub-row: tokens + decision -->
					{#if step.name === 'llm' && perCall}
						<div
							class="flex flex-wrap items-center gap-x-3 gap-y-0.5 border-t px-3 py-1.5 text-[10px]"
							style="border-color:var(--ds-border)"
						>
							<span class="text-blue-400">{fmtTokens(perCall.prompt_tokens)} prompt</span>
							<span class="text-emerald-400">{fmtTokens(perCall.completion_tokens)} completion</span
							>
							{#if perCall.phase === 'tool_call' && decisions.length > 0}
								<span class="text-amber-300">
									→ {decisions.map((d) => d.name).join(', ')}
								</span>
							{:else if perCall.phase === 'final'}
								<span class="text-emerald-300">→ generating response</span>
							{/if}
						</div>
					{/if}

					<!-- Dispatch sub-row: tool call results -->
					{#if step.name === 'dispatch' && dispatchCalls.length > 0}
						<div class="border-t px-3 py-1.5" style="border-color:var(--ds-border)">
							{#each dispatchCalls as call}
								{@const httpStatus = extractHttpStatus(call.output)}
								<div class="flex items-center gap-1.5 py-0.5 text-[10px]">
									<span
										class="font-mono {call.kind === 'skill'
											? 'text-emerald-400'
											: 'text-amber-300'}">{call.name}</span
									>
									{#if httpStatus !== null}
										<span
											class="rounded px-1 py-0 font-mono text-[9px] {statusBadgeClass(httpStatus)}"
											>{httpStatus}</span
										>
									{/if}
									{#if call.error}
										<span class="text-[9px] text-red-400">error</span>
									{/if}
								</div>
							{/each}
						</div>
					{/if}

					<!-- Error row -->
					{#if step.error}
						<div
							class="border-t px-3 py-1.5 text-[10px] text-red-400"
							style="border-color:var(--ds-border)"
						>
							{step.error}
						</div>
					{/if}
				</button>
			{/each}

			{#if trace.final_response}
				<button
					type="button"
					onclick={() => (selectedNodeId = selectedNodeId === '__output__' ? null : '__output__')}
					class="w-full overflow-hidden rounded-xl border text-left transition-colors hover:border-blue-500/30 {selectedNodeId ===
					'__output__'
						? 'border-blue-500/40'
						: ''}"
					style="border-color:{selectedNodeId === '__output__' ? '' : 'var(--ds-border)'}"
				>
					<div
						class="flex items-center gap-2 px-3 py-2.5"
						style="background:{selectedNodeId === '__output__'
							? 'color-mix(in srgb,#3b82f6 8%,transparent)'
							: 'var(--canvas)'}"
					>
						<span class="w-5 shrink-0 text-center font-mono text-[10px] text-muted-foreground/50"
							>✓</span
						>
						<span
							class="font-mono text-[11px] font-semibold"
							style="color:{nodeTextColor('__output__')}">response</span
						>
						{#if trace.token_usage}
							<span class="ml-auto shrink-0 font-mono text-[10px] text-purple-400/80"
								>{fmtTokens(trace.token_usage.total_tokens)} tok</span
							>
						{:else}
							<span class="ml-auto shrink-0 font-mono text-[10px] text-emerald-400/60"
								>{fmtMs(trace.duration_ms)}</span
							>
						{/if}
					</div>
				</button>
			{/if}

			<!-- Guardrails/constraints summary (if configured) -->
			{#if trace.system_prompt_sections.some((s) => s.label === 'guardrails' && s.content) || trace.system_prompt_sections.some((s) => s.label === 'constraints' && s.content)}
				<div
					class="mt-3 rounded-xl border px-3 py-2 text-[10px]"
					style="border-color:var(--ds-border);background:color-mix(in srgb,#f59e0b 5%,transparent)"
				>
					<p class="mb-1.5 font-semibold tracking-wider text-amber-400 uppercase">
						Active constraints &amp; guardrails
					</p>
					<div class="space-y-0.5 text-muted-foreground/80">
						{#each trace.system_prompt_sections.filter((s) => (s.label === 'guardrails' || s.label === 'constraints') && s.content) as section}
							<div class="flex items-center gap-1.5">
								<span
									class="rounded px-1 py-0 text-[9px] font-semibold tracking-wider uppercase {section.label ===
									'guardrails'
										? 'bg-amber-500/10 text-amber-400'
										: 'bg-orange-500/10 text-orange-400'}">{section.label}</span
								>
								<span class="truncate">{section.content.length} chars configured</span>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	{:else}
		<div class="flex h-full items-center justify-center text-center">
			<div class="max-w-sm">
				<Bot class="mx-auto mb-3 size-8 text-muted-foreground" />
				<p class="text-sm text-muted-foreground">
					Send a message in the Test Agent panel to see the execution trace here.
				</p>
			</div>
		</div>
	{/if}
{/snippet}

{#if !isStaticMode && !debSessId && !isLiveRunActive}
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
						{#if isLiveRunActive}
							{liveSteps.length > 0
								? `${liveSteps.length} node${liveSteps.length !== 1 ? 's' : ''} executing…`
								: 'Connecting…'}
						{:else if metadata}
							{(trace?.node_timings ?? []).length} steps · {trace ? fmtMs(trace.duration_ms) : ''}
						{:else}
							No trace loaded
						{/if}
					</p>
				</div>
			</div>
			<div class="flex items-center gap-3">
				{#if runs.length > 0}
					<span class="text-[11px] text-muted-foreground">
						{runs.length} message{runs.length !== 1 ? 's' : ''}
						{#if sessionTotalTokens > 0}
							<span class="opacity-50"> · </span>
							<span class="font-mono text-purple-400" title="Total tokens across session"
								>{fmtTokens(sessionTotalTokens)} tok</span
							>
						{/if}
					</span>
				{/if}
				{#if isLiveRunActive}
					<span
						class="flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-[10px] font-semibold tracking-wider text-emerald-400 uppercase"
					>
						<Spinner class="size-2.5" />
						live
					</span>
				{:else if !isStaticMode && debSessId}
					<span
						class="rounded-full bg-emerald-500/10 px-2.5 py-1 text-[10px] font-semibold tracking-wider text-emerald-400 uppercase"
					>
						● live
					</span>
				{/if}
			</div>
		</header>

		<div class="flex min-h-0 flex-1 flex-col">
			<div class="flex min-h-0 flex-1">
				<!-- Message history sidebar -->
				{#if runs.length > 0 || isLiveRunActive}
					<aside
						class="w-[200px] shrink-0 overflow-y-auto border-r"
						style="border-color:var(--ds-border);background:var(--surface)"
					>
						<div
							class="sticky top-0 border-b bg-[var(--surface)] px-3 py-2 text-[10px] font-semibold tracking-wider text-primary uppercase"
							style="border-color:var(--ds-border)"
						>
							Messages
						</div>
						{#if isLiveRunActive}
							<div
								class="w-full border-b bg-[var(--surface-hover)] px-3 py-2.5"
								style="border-color:var(--ds-border)"
							>
								<div class="flex items-center gap-2">
									<Spinner class="size-2.5 shrink-0 text-emerald-400" />
									<span class="text-[11px] font-semibold text-emerald-400">Running…</span>
								</div>
								<p class="mt-1 truncate text-[11px] leading-tight text-foreground/60 italic">
									{liveSteps.find((s) => s.status === 'running')?.name ?? 'in progress'}
								</p>
							</div>
						{/if}
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
									<div class="flex min-w-0 items-center gap-2">
										<span
											class="flex size-5 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold"
											style="background:color-mix(in srgb, #3b82f6 12%, transparent);color:var(--text-main)"
											>{runs.length - idx}</span
										>
										<span class="truncate font-mono text-[10px] text-muted-foreground"
											>{fmtTime(run.started_at)}</span
										>
									</div>
									{#if listItemTrackedTokens(run) > 0}
										<span
											class="shrink-0 rounded bg-purple-500/10 px-1.5 py-0.5 font-mono text-[9px] text-purple-400"
											title={listItemTokenTitle(run)}
											>{fmtTokens(listItemTrackedTokens(run))} tok</span
										>
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
					{#if loading && !trace && !isLiveRunActive}
						<div class="flex flex-1 items-center justify-center text-sm text-muted-foreground">
							<Spinner class="mr-2 size-4" />
							Loading trace…
						</div>
					{:else if error && !isLiveRunActive}
						<div class="flex flex-1 items-center justify-center px-6">
							<div
								class="max-w-md rounded-xl border bg-[var(--canvas)] p-6 text-center text-sm"
								style="border-color:var(--ds-border)"
							>
								<Bot class="mx-auto mb-3 size-8 text-muted-foreground" />
								<p>{error}</p>
							</div>
						</div>
					{:else if isLiveRunActive || (trace && metadata)}
						<div class="flex min-h-0 flex-1">
							<!-- Execution timeline -->
							<div
								class="w-[280px] shrink-0 overflow-y-auto border-r"
								style="border-color:var(--ds-border);background:var(--canvas)"
							>
								{@render executionTimeline()}
							</div>

							<!-- Detail panel -->
							<div class="flex-1 overflow-y-auto p-5 pb-8">
								{#if !selectedStep}
									{@render runOverview()}
								{:else if selectedStep.name === '__input__'}
									{@render detailHeader('User message', 'Run input', User)}
									<div
										class="rich-trace-message rounded-xl border bg-[var(--canvas)] p-4 text-sm leading-relaxed"
										style="border-color:var(--ds-border)"
									>
										{@html renderTraceMessage(trace?.user_message)}
									</div>
								{:else if selectedStep.name === 'rag'}
									{@render detailHeader(
										'RAG',
										`Retrieval · ${selectedStep.duration_ms != null ? fmtMs(selectedStep.duration_ms) : selectedStep.status}`,
										Database
									)}
									{#if !trace}
										{@render liveStepInfo(selectedStep)}
									{:else}
										<div class="space-y-3">
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
											{#if trace.rag_error}
												<p
													class="rounded-xl border bg-red-500/5 p-4 text-xs text-red-400"
													style="border-color:color-mix(in srgb, var(--ds-border) 50%, #ef4444 50%)"
												>
													<strong>Retrieval error:</strong>
													{trace.rag_error}
												</p>
											{/if}
											{#if trace.retrieved_chunks.length === 0}
												{#if trace.rag_scope.length === 0}
													<p
														class="rounded-xl border bg-zinc-500/5 p-4 text-xs text-muted-foreground"
														style="border-color:var(--ds-border)"
													>
														No RAG scope configured for this instance.
													</p>
												{:else}
													<p
														class="rounded-xl border bg-amber-500/5 p-4 text-xs text-amber-300"
														style="border-color:color-mix(in srgb, var(--ds-border) 50%, #f59e0b 50%)"
													>
														No chunks above the similarity threshold.
													</p>
												{/if}
											{:else}
												<p
													class="mb-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase"
												>
													{trace.retrieved_chunks.length} chunk{trace.retrieved_chunks.length !== 1
														? 's'
														: ''} retrieved
												</p>
												<ol class="space-y-2">
													{#each trace.retrieved_chunks as chunk, idx (idx)}
														<li
															class="rounded-xl border bg-[var(--canvas)] p-3"
															style="border-color:var(--ds-border)"
														>
															<div class="mb-1.5 flex items-center justify-between">
																<span
																	class="flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground"
																>
																	<FileText class="size-3" />
																	{chunk.filename ?? chunk.source ?? `chunk #${idx + 1}`}
																</span>
																<span
																	class="rounded bg-emerald-500/10 px-1.5 py-0.5 font-mono text-[10px] text-emerald-400"
																	>score {fmtScore(chunk.score)}</span
																>
															</div>
															<p class="text-xs leading-relaxed text-foreground/80">{chunk.text}</p>
														</li>
													{/each}
												</ol>
											{/if}
										</div>
									{/if}
								{:else if selectedStep.name === 'llm'}
									{@const llmIter = llmIterationForStep(selectedStep.step)}
									{@const perCall = perCallForLlmStep(selectedStep.step)}
									{@const decisions = toolDecisionsForLlmStep(selectedStep.step)}
									{@render detailHeader(
										`LLM · iteration ${llmIter >= 0 ? llmIter : '?'}`,
										`${trace?.model ?? '?'} · ${perCall?.phase === 'final' ? 'final response' : `→ ${decisions.length} tool${decisions.length !== 1 ? 's' : ''}`} · ${selectedStep.duration_ms != null ? fmtMs(selectedStep.duration_ms) : '—'}`,
										Bot
									)}
									{#if !trace}
										{@render liveStepInfo(selectedStep)}
									{:else}
										<div class="space-y-3">
											<!-- Per-iteration token usage -->
											{#if perCall}
												<div
													class="rounded-xl border bg-[var(--canvas)] p-3"
													style="border-color:var(--ds-border)"
												>
													<p
														class="mb-2 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase"
													>
														Token Usage · Iteration {perCall.iteration ?? llmIter}
														{#if perCall.phase}
															<span
																class="ml-1.5 rounded px-1.5 py-0.5 text-[9px] tracking-normal normal-case {perCall.phase ===
																'final'
																	? 'bg-emerald-500/10 text-emerald-400'
																	: 'bg-amber-500/10 text-amber-400'}">{perCall.phase}</span
															>
														{/if}
													</p>
													<div class="grid grid-cols-3 gap-2 text-xs">
														<div class="rounded-md bg-blue-500/10 p-2">
															<p class="text-[10px] tracking-wider text-muted-foreground uppercase">
																Prompt
															</p>
															<p class="font-mono text-base font-semibold text-blue-400">
																{fmtTokens(perCall.prompt_tokens)}
															</p>
														</div>
														<div class="rounded-md bg-emerald-500/10 p-2">
															<p class="text-[10px] tracking-wider text-muted-foreground uppercase">
																Completion
															</p>
															<p class="font-mono text-base font-semibold text-emerald-400">
																{fmtTokens(perCall.completion_tokens)}
															</p>
														</div>
														<div class="rounded-md bg-purple-500/10 p-2">
															<p class="text-[10px] tracking-wider text-muted-foreground uppercase">
																Total
															</p>
															<p class="font-mono text-base font-semibold text-purple-400">
																{fmtTokens(perCall.total_tokens)}
															</p>
														</div>
													</div>
												</div>
											{/if}

											<!-- Tool decisions from this LLM iteration -->
											{#if decisions.length > 0}
												<div
													class="rounded-xl border bg-[var(--canvas)] p-3"
													style="border-color:var(--ds-border)"
												>
													<p
														class="mb-2 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase"
													>
														Tool decisions ({decisions.length})
													</p>
													<div class="flex flex-wrap gap-1.5">
														{#each decisions as d}
															<span
																class="rounded-md px-2 py-1 font-mono text-[11px] font-semibold {d.kind ===
																'skill'
																	? 'bg-emerald-500/10 text-emerald-400'
																	: 'bg-amber-500/10 text-amber-400'}">{d.name}</span
															>
														{/each}
													</div>
												</div>
											{:else if perCall?.phase === 'final'}
												<div
													class="rounded-xl border bg-emerald-500/5 p-3 text-xs text-emerald-400"
													style="border-color:color-mix(in srgb,var(--ds-border) 50%,#22c55e 50%)"
												>
													This iteration generated the final response — no further tool calls.
												</div>
											{/if}

											{#if perCall?.output_text || perCall?.phase === 'final'}
												<div
													class="rounded-xl border bg-[var(--canvas)] p-3"
													style="border-color:var(--ds-border)"
												>
													<p
														class="mb-2 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase"
													>
														Generated response
													</p>
													<div
														class="rich-trace-message max-h-96 overflow-auto rounded-md bg-zinc-500/5 p-3 text-sm leading-relaxed text-foreground/90"
													>
														{@html renderTraceMessage(perCall.output_text || trace.final_response)}
													</div>
												</div>
											{/if}

											{#if perCall?.tool_calls?.length}
												<div
													class="rounded-xl border bg-[var(--canvas)] p-3"
													style="border-color:var(--ds-border)"
												>
													<p
														class="mb-2 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase"
													>
														Raw tool calls
													</p>
													<pre
														class="max-h-72 overflow-auto rounded-md bg-zinc-500/5 p-2 font-mono text-[11px] leading-relaxed text-foreground/80">{fmtJson(
															perCall.tool_calls
														)}</pre>
												</div>
											{/if}

											<!-- Guardrails & constraints (shown once on first LLM) -->
											{#if llmIter === 0}
												{#each trace.system_prompt_sections.filter((s) => (s.label === 'guardrails' || s.label === 'constraints') && s.content) as section}
													<details
														class="rounded-xl border bg-[var(--canvas)]"
														style="border-color:var(--ds-border)"
													>
														<summary
															class="flex cursor-pointer items-center gap-2 px-3 py-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase"
														>
															<span
																class="rounded px-1.5 py-0.5 text-[9px] tracking-wider {section.label ===
																'guardrails'
																	? 'bg-amber-500/10 text-amber-400'
																	: 'bg-orange-500/10 text-orange-400'}">{section.label}</span
															>
															{section.label} ({section.content.length} chars)
														</summary>
														<pre
															class="border-t px-3 py-2 font-mono text-[11px] leading-relaxed break-words whitespace-pre-wrap"
															style="border-color:var(--ds-border)">{section.content}</pre>
													</details>
												{/each}

												<!-- Available tools/skills on first LLM iteration -->
												{#if trace.available_tools.length > 0 || trace.available_skills.length > 0}
													<div
														class="rounded-xl border bg-[var(--canvas)] p-3"
														style="border-color:var(--ds-border)"
													>
														<p
															class="mb-1.5 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase"
														>
															Capabilities in scope
														</p>
														<div class="flex flex-wrap gap-1">
															{#each trace.available_tools as tool}
																<span
																	class="rounded bg-blue-500/10 px-1.5 py-0.5 font-mono text-[10px] text-blue-400"
																	>{tool}</span
																>
															{/each}
															{#each trace.available_skills as skill}
																<span
																	class="rounded bg-emerald-500/10 px-1.5 py-0.5 font-mono text-[10px] text-emerald-400"
																	>{skill}</span
																>
															{/each}
														</div>
													</div>
												{/if}

												<!-- System prompt sections (core + instruction blocks) -->
												{#each trace.system_prompt_sections.filter((s) => s.label !== 'guardrails' && s.label !== 'constraints' && s.content) as section (section.label)}
													<details
														class="rounded-xl border bg-[var(--canvas)]"
														style="border-color:var(--ds-border)"
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
												{/each}

												{@render promptContextPanel()}
											{/if}
										</div>
									{/if}
								{:else if selectedStep.name === 'dispatch'}
									{@const dispatchCalls = toolCallsForDispatchStep(selectedStep.step)}
									{@const dispatchIter = dispatchIterationForStep(selectedStep.step)}
									{@render detailHeader(
										`Dispatch · iteration ${dispatchIter > 0 ? dispatchIter : '?'}`,
										`${dispatchCalls.length} tool execution${dispatchCalls.length !== 1 ? 's' : ''} · ${selectedStep.duration_ms != null ? fmtMs(selectedStep.duration_ms) : selectedStep.status}`,
										Wrench
									)}
									{#if !trace}
										{@render liveStepInfo(selectedStep)}
									{:else if dispatchCalls.length === 0}
										<p class="text-sm text-muted-foreground">
											No tool executions recorded for this step.
										</p>
									{:else}
										{@render toolCallList(dispatchCalls)}
									{/if}
								{:else if selectedStep.name === 'handoff'}
									{@const targetName =
										trace?.handoff_target_name ||
										(trace?.handoff_target ? `#${trace.handoff_target.slice(0, 8)}` : null)}
									{@render detailHeader(
										'Handoff',
										targetName ? `→ ${targetName}` : selectedStep.status,
										GitBranch
									)}
									{#if !trace}
										{@render liveStepInfo(selectedStep)}
									{:else if trace.handoff_target}
										<div class="space-y-3">
											<div
												class="rounded-xl border p-3"
												style="border-color:color-mix(in srgb,#f97316 30%,var(--ds-border));background:color-mix(in srgb,#f97316 6%,transparent)"
											>
												<p
													class="mb-0.5 text-[10px] font-semibold tracking-wider text-orange-400/70 uppercase"
												>
													Transferred to
												</p>
												<p class="text-sm font-semibold text-orange-300">
													{targetName ?? trace.handoff_target}
												</p>
												<p class="mt-0.5 font-mono text-[10px] text-muted-foreground/60">
													{trace.handoff_target}
												</p>
											</div>
											{#if trace.handoff_summary}
												<div
													class="rounded-xl border bg-canvas p-3"
													style="border-color:var(--ds-border)"
												>
													<p
														class="mb-1.5 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase"
													>
														Transfer reason
													</p>
													<p class="text-xs leading-relaxed text-foreground/80">
														{trace.handoff_summary}
													</p>
												</div>
											{/if}
											{#if trace.linked_agents.length > 0}
												{@const linkedAgents = trace.linked_agents as Array<
													Record<string, unknown>
												>}
												{@const matchedLink = linkedAgents.find(
													(l) => l['target_instance_id'] === trace!.handoff_target
												)}
												{#if matchedLink}
													<div
														class="rounded-xl border bg-canvas p-3"
														style="border-color:var(--ds-border)"
													>
														<p
															class="mb-2 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase"
														>
															Link configuration
														</p>
														<dl class="space-y-1.5 text-xs">
															<div class="flex justify-between gap-3">
																<dt class="text-muted-foreground">Tool name</dt>
																<dd class="font-mono text-amber-300">
																	{String(matchedLink['transfer_tool_name'] ?? '—')}
																</dd>
															</div>
															<div class="flex justify-between gap-3">
																<dt class="text-muted-foreground">Mode</dt>
																<dd class="font-mono text-blue-400">
																	{String(matchedLink['transfer_mode'] ?? '—')}
																</dd>
															</div>
															{#if matchedLink['context_policy']}
																{@const policy = matchedLink['context_policy'] as Record<
																	string,
																	unknown
																>}
																<div class="flex justify-between gap-3">
																	<dt class="text-muted-foreground">Context policy</dt>
																	<dd class="font-mono text-purple-400">
																		{Object.entries(policy)
																			.filter(([, v]) => v)
																			.map(([k]) => k.replace(/_/g, ' '))
																			.join(', ') || 'default'}
																	</dd>
																</div>
															{/if}
														</dl>
													</div>
												{/if}
											{/if}

											{#if trace.handoff_context}
												{@const hctx = trace.handoff_context}
												{#if hctx.summary}
													<div
														class="rounded-xl border bg-canvas p-3"
														style="border-color:var(--ds-border)"
													>
														<p
															class="mb-2 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase"
														>
															Transfer summary
														</p>
														<dl class="space-y-2 text-xs">
															{#if hctx.summary.user_goal}
																<div>
																	<dt
																		class="mb-0.5 text-[10px] tracking-wider text-muted-foreground uppercase"
																	>
																		User goal
																	</dt>
																	<dd class="leading-relaxed text-foreground/80">
																		{hctx.summary.user_goal}
																	</dd>
																</div>
															{/if}
															{#if hctx.summary.known_facts?.length}
																<div>
																	<dt
																		class="mb-0.5 text-[10px] tracking-wider text-muted-foreground uppercase"
																	>
																		Known facts
																	</dt>
																	<dd class="space-y-0.5">
																		{#each hctx.summary.known_facts as fact}
																			<p class="leading-relaxed text-foreground/80">– {fact}</p>
																		{/each}
																	</dd>
																</div>
															{/if}
															{#if hctx.summary.actions_already_taken?.length}
																<div>
																	<dt
																		class="mb-0.5 text-[10px] tracking-wider text-muted-foreground uppercase"
																	>
																		Actions taken
																	</dt>
																	<dd class="space-y-0.5">
																		{#each hctx.summary.actions_already_taken as action}
																			<p class="leading-relaxed text-foreground/80">– {action}</p>
																		{/each}
																	</dd>
																</div>
															{/if}
															{#if hctx.summary.custom_instructions}
																<div>
																	<dt
																		class="mb-0.5 text-[10px] tracking-wider text-muted-foreground uppercase"
																	>
																		Custom instructions
																	</dt>
																	<dd class="leading-relaxed text-foreground/80">
																		{hctx.summary.custom_instructions}
																	</dd>
																</div>
															{/if}
														</dl>
													</div>
												{/if}

												{#if hctx.handoff_messages?.length}
													<details
														class="rounded-xl border bg-canvas"
														style="border-color:var(--ds-border)"
													>
														<summary
															class="cursor-pointer px-3 py-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase"
														>
															Context sent to target
															<span class="ml-1.5 text-[10px] text-muted-foreground/60 normal-case"
																>({hctx.handoff_messages.length} message{hctx.handoff_messages
																	.length !== 1
																	? 's'
																	: ''})</span
															>
														</summary>
														<ol
															class="space-y-2 border-t p-3"
															style="border-color:var(--ds-border)"
														>
															{#each hctx.handoff_messages as msg, i (i)}
																<li
																	class="rounded-lg border bg-zinc-500/5 p-2.5"
																	style="border-color:var(--ds-border)"
																>
																	<div class="mb-1.5 flex items-center justify-between">
																		<span
																			class="rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold {msg.role ===
																			'user'
																				? 'bg-blue-500/10 text-blue-400'
																				: 'bg-emerald-500/10 text-emerald-400'}">{msg.role}</span
																		>
																		<span class="font-mono text-[10px] text-muted-foreground/50"
																			>#{i + 1}</span
																		>
																	</div>
																	<div
																		class="rich-trace-message max-h-48 overflow-auto rounded bg-black/10 p-2 text-[11px] leading-relaxed break-words text-foreground/80"
																	>
																		{@html renderTraceMessage(msg.content)}
																	</div>
																</li>
															{/each}
														</ol>
													</details>
												{/if}

												{#if hctx.sanitized_messages?.length}
													<details
														class="rounded-xl border bg-canvas"
														style="border-color:var(--ds-border)"
													>
														<summary
															class="cursor-pointer px-3 py-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase"
														>
															Sanitized source conversation
															<span class="ml-1.5 text-[10px] text-muted-foreground/60 normal-case"
																>({hctx.sanitized_messages.length} msg)</span
															>
														</summary>
														<ol
															class="space-y-2 border-t p-3"
															style="border-color:var(--ds-border)"
														>
															{#each hctx.sanitized_messages as msg, i (i)}
																<li
																	class="rounded-lg border bg-zinc-500/5 p-2.5"
																	style="border-color:var(--ds-border)"
																>
																	<span
																		class="rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold {msg.role ===
																		'user'
																			? 'bg-blue-500/10 text-blue-400'
																			: 'bg-emerald-500/10 text-emerald-400'}">{msg.role}</span
																	>
																	<div
																		class="rich-trace-message mt-1.5 max-h-32 overflow-auto rounded bg-black/10 p-2 text-[11px] leading-relaxed break-words text-foreground/70"
																	>
																		{@html renderTraceMessage(msg.content)}
																	</div>
																</li>
															{/each}
														</ol>
													</details>
												{/if}
											{/if}
										</div>
									{:else}
										<p class="text-sm text-muted-foreground">No handoff data recorded.</p>
									{/if}
								{:else if selectedStep.name === '__output__'}
									{@render detailHeader(
										'Final response',
										`${trace ? fmtMs(trace.duration_ms) : '—'} total · ${trace?.model ?? '?'}`,
										MessageSquare
									)}
									{#if trace}
										<div class="space-y-3">
											<div
												class="rich-trace-message rounded-xl border bg-[var(--canvas)] p-4 text-sm leading-relaxed"
												style="border-color:var(--ds-border)"
											>
												{@html renderTraceMessage(trace.final_response)}
											</div>
											{#if trace.token_usage}
												<div
													class="rounded-xl border bg-[var(--canvas)] p-3"
													style="border-color:var(--ds-border)"
												>
													<p
														class="mb-2 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase"
													>
														Total Token Usage ({trace.token_usage.llm_calls} LLM call{trace
															.token_usage.llm_calls === 1
															? ''
															: 's'})
													</p>
													<div class="grid grid-cols-3 gap-2 text-xs">
														<div class="rounded-md bg-blue-500/10 p-2">
															<p class="text-[10px] tracking-wider text-muted-foreground uppercase">
																Prompt
															</p>
															<p class="font-mono text-base font-semibold text-blue-400">
																{fmtTokens(trace.token_usage.prompt_tokens)}
															</p>
														</div>
														<div class="rounded-md bg-emerald-500/10 p-2">
															<p class="text-[10px] tracking-wider text-muted-foreground uppercase">
																Completion
															</p>
															<p class="font-mono text-base font-semibold text-emerald-400">
																{fmtTokens(trace.token_usage.completion_tokens)}
															</p>
														</div>
														<div class="rounded-md bg-purple-500/10 p-2">
															<p class="text-[10px] tracking-wider text-muted-foreground uppercase">
																Total
															</p>
															<p class="font-mono text-base font-semibold text-purple-400">
																{fmtTokens(trace.token_usage.total_tokens)}
															</p>
														</div>
													</div>
													{#if trace.token_usage.embedding_tokens > 0}
														<div
															class="mt-2 flex items-center gap-2 rounded-md bg-amber-500/10 p-2 text-xs"
														>
															<Database class="size-3 text-amber-400" />
															<span class="text-[11px] text-muted-foreground"
																>Embeddings ({trace.token_usage.embedding_calls} call):</span
															>
															<span class="font-mono text-amber-400"
																>{fmtTokens(trace.token_usage.embedding_tokens)} tok</span
															>
														</div>
													{/if}
													{#if trace.token_usage.per_call.length > 1}
														<details class="mt-2">
															<summary
																class="cursor-pointer text-[10px] font-semibold tracking-wider text-muted-foreground uppercase"
															>
																Per-iteration breakdown ({trace.token_usage.per_call.length})
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
																			<td class="py-1 text-muted-foreground/80"
																				>{call.phase ?? '—'}</td
																			>
																			<td class="py-1 text-right text-blue-400"
																				>{fmtTokens(call.prompt_tokens)}</td
																			>
																			<td class="py-1 text-right text-emerald-400"
																				>{fmtTokens(call.completion_tokens)}</td
																			>
																			<td class="py-1 text-right text-purple-400"
																				>{fmtTokens(call.total_tokens)}</td
																			>
																		</tr>
																	{/each}
																</tbody>
															</table>
														</details>
													{/if}
												</div>
											{/if}
										</div>
									{:else}
										<p class="text-sm text-muted-foreground">Waiting for run to complete…</p>
									{/if}
								{:else}
									{@render liveStepInfo(selectedStep)}
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

		{#if trace && metadata && !isLiveRunActive}
			<footer
				class="flex shrink-0 items-center gap-3 overflow-x-auto border-t px-4 py-1.5 text-[10px] text-muted-foreground/70"
				style="border-color:var(--ds-border);background:var(--surface)"
			>
				<span class="shrink-0 font-mono text-primary">#{metadata.run_id.slice(0, 8)}</span>
				<span class="opacity-40">·</span>
				<span class="shrink-0 text-primary">{fmtMs(trace.duration_ms)}</span>
				{#if trace.token_usage}
					<span class="opacity-40">·</span>
					<span class="shrink-0 font-mono text-blue-400" title="Prompt tokens"
						>P {fmtTokens(trace.token_usage.prompt_tokens)}</span
					>
					<span class="opacity-40">/</span>
					<span class="shrink-0 font-mono text-emerald-400" title="Completion tokens"
						>C {fmtTokens(trace.token_usage.completion_tokens)}</span
					>
					<span class="opacity-40">/</span>
					<span
						class="shrink-0 font-mono text-amber-400"
						title={`Embedding tokens across ${trace.token_usage.embedding_calls} call(s)`}
						>E {fmtTokens(trace.token_usage.embedding_tokens)}</span
					>
					<span class="opacity-40">/</span>
					<span class="shrink-0 font-mono text-purple-400" title="Total LLM and embedding tokens"
						>T {fmtTokens(traceTrackedTokens(trace))}</span
					>
				{/if}
				<span class="opacity-40">·</span>
				<span class="shrink-0 text-primary">{trace.model ?? '?'}</span>
				<span class="opacity-40">·</span>
				<span class="shrink-0 text-primary">{trace.ai_provider ?? '?'}</span>
				<span class="opacity-40">·</span>
				<span class="shrink-0 text-primary"
					>{new Date(metadata.created_at).toLocaleString('pt-BR')}</span
				>
			</footer>
		{/if}
	</div>
{/if}

{#snippet liveStepInfo(step: {
	name: string;
	step: number | null;
	status: string;
	duration_ms?: number;
	error?: string | null;
	triggers?: string[] | null;
})}
	<div class="space-y-3">
		<div class="rounded-xl border bg-[var(--canvas)] p-3" style="border-color:var(--ds-border)">
			<dl class="space-y-2 font-mono text-xs">
				<div class="flex justify-between">
					<dt class="text-muted-foreground">Node</dt>
					<dd class="font-semibold" style="color:{nodeTextColor(step.name)}">{step.name}</dd>
				</div>
				{#if step.step !== null}
					<div class="flex justify-between">
						<dt class="text-muted-foreground">Step</dt>
						<dd>{step.step}</dd>
					</div>
				{/if}
				<div class="flex justify-between">
					<dt class="text-muted-foreground">Status</dt>
					<dd
						class={step.status === 'running'
							? 'text-amber-400'
							: step.status === 'error'
								? 'text-red-400'
								: 'text-emerald-400'}
					>
						{step.status}
					</dd>
				</div>
				{#if step.duration_ms != null}
					<div class="flex justify-between">
						<dt class="text-muted-foreground">Duration</dt>
						<dd class="text-emerald-400">{fmtMs(step.duration_ms)}</dd>
					</div>
				{/if}
				{#if step.triggers?.length}
					<div class="flex justify-between">
						<dt class="text-muted-foreground">Triggered by</dt>
						<dd>{stepTriggerLabel(step.triggers)}</dd>
					</div>
				{/if}
			</dl>
		</div>
		{#if step.error}
			<p
				class="rounded-xl border bg-red-500/5 p-3 text-xs text-red-400"
				style="border-color:color-mix(in srgb,var(--ds-border) 50%,#ef4444 50%)"
			>
				{step.error}
			</p>
		{/if}
		{#if step.status === 'running'}
			<div class="flex items-center gap-2 text-xs text-muted-foreground">
				<Spinner class="size-3" />
				<span>Trace details available after this run completes.</span>
			</div>
		{/if}
	</div>
{/snippet}
