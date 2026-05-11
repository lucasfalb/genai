<script lang="ts">
	import { mode } from 'mode-watcher';
	import { type Component } from 'svelte';
	import { SvelteFlow, Background, Controls } from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';
	import Bot from '@lucide/svelte/icons/bot';
	import Database from '@lucide/svelte/icons/database';
	import FileText from '@lucide/svelte/icons/file-text';
	import Wrench from '@lucide/svelte/icons/wrench';
	import GitBranch from '@lucide/svelte/icons/git-branch';
	import MessageSquare from '@lucide/svelte/icons/message-square';
	import User from '@lucide/svelte/icons/user';
	import X from '@lucide/svelte/icons/x';
	import type { RunTracePayload, RunTraceResponse } from '$lib/api/types';

	let { trace, metadata }: { trace: RunTracePayload; metadata: RunTraceResponse } = $props();

	let selectedNode = $state<string | null>(null);
	let isDark = $derived(mode.current === 'dark');

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

	function timingFor(nodeName: string): number | null {
		if (!trace) return null;
		const matches = (trace.node_timings ?? []).filter((entry) => entry.name === nodeName);
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

	const activeNodes = $derived.by(() => {
		if (!trace) return [];
		const list: NodeDescriptor[] = [];
		list.push({ id: 'user', label: 'User message', icon: User, tone: 'neutral', duration: null });
		if (trace.rag_scope.length > 0 || trace.retrieved_chunks.length > 0) {
			list.push({
				id: 'rag',
				label:
					trace.retrieved_chunks.length > 0
						? `RAG · ${trace.retrieved_chunks.length} chunks`
						: 'RAG · no hits',
				icon: Database,
				tone: trace.retrieved_chunks.length > 0 ? 'ok' : 'warn',
				duration: timingFor('rag')
			});
		}
		list.push({
			id: 'llm',
			label: `LLM · ${trace.model ?? '?'}`,
			icon: Bot,
			tone: 'used',
			duration: timingFor('llm')
		});
		if (trace.pending_tool_calls.length > 0) {
			list.push({
				id: 'tools',
				label: `Tools · ${trace.pending_tool_calls.length} call${trace.pending_tool_calls.length > 1 ? 's' : ''}`,
				icon: Wrench,
				tone: 'warn',
				duration: timingFor('dispatch')
			});
		}
		if (trace.handoff_target) {
			list.push({
				id: 'handoff',
				label: `Handoff · #${trace.handoff_target.slice(0, 6)}`,
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
			duration: trace.duration_ms
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

<div class="relative flex h-full">
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
							<Background bgColor={isDark ? '#050505' : '#f8fafc'} gap={20} patternColor={isDark ? '#27272a' : '#d4d4d8'} />
			<Controls position="bottom-right" showLock={false} />
		</SvelteFlow>
	</div>

	<div class="flex-1 overflow-y-auto p-6 pb-16">
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
		{:else if selectedNode === 'rag'}
			{@render detailHeader(
				'RAG Context',
				`${trace.retrieved_chunks.length} chunks above threshold · scope ${trace.rag_scope.length}`,
				Database
			)}
			{#if trace.retrieved_chunks.length === 0}
				{#if trace.rag_scope.length === 0}
					<p
						class="rounded-xl border bg-zinc-500/5 p-4 text-xs text-muted-foreground"
						style="border-color:var(--ds-border)"
					>
						Instance has no RAG scope. Configure collections in
						<code class="font-mono">rag_scope</code>.
					</p>
				{:else}
					<p
						class="rounded-xl border bg-amber-500/5 p-4 text-xs text-amber-300"
						style="border-color:color-mix(in srgb, var(--ds-border) 50%, #f59e0b 50%)"
					>
						No chunks above the similarity threshold (<code class="font-mono">RAG_SCORE_THRESHOLD</code>). Reword the query or lower the threshold.
					</p>
				{/if}
			{:else}
				<ol class="space-y-2">
					{#each trace.retrieved_chunks as chunk, idx (idx)}
						<li
							class="rounded-xl border bg-[var(--canvas)] p-3"
							style="border-color:var(--ds-border)"
						>
							<div class="mb-1.5 flex items-center justify-between">
								<span class="flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground">
									<FileText class="size-3" />
									{chunk.filename ?? chunk.source ?? `chunk #${idx + 1}`}
								</span>
								<span
									class="rounded bg-emerald-500/10 px-1.5 py-0.5 font-mono text-[10px] text-emerald-400"
								>
									score {fmtScore(chunk.score)}
								</span>
							</div>
							<p class="text-xs leading-relaxed text-foreground/80">{chunk.text}</p>
						</li>
					{/each}
				</ol>
			{/if}
		{:else if selectedNode === 'llm'}
			{@render detailHeader(
				'LLM',
				`${trace.model ?? '?'} · ${trace.ai_provider ?? '?'} · temperature ${trace.temperature?.toFixed?.(2) ?? '—'}`,
				Bot
			)}
			<div class="space-y-2">
				<p class="text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
					Layered system prompt
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
			</div>
		{:else if selectedNode === 'tools'}
			{@render detailHeader(
				'Tool calls',
				`${trace.pending_tool_calls.length} call(s) suggested by the model`,
				Wrench
			)}
			<ol class="space-y-2">
				{#each trace.pending_tool_calls as call, idx (idx)}
					<li
						class="rounded-xl border bg-[var(--canvas)] p-3"
						style="border-color:var(--ds-border)"
					>
						<p class="font-mono text-xs">
							<span class="text-blue-400">{call.name ?? '(unnamed)'}</span>
						</p>
						<pre class="mt-1 overflow-x-auto font-mono text-[11px] text-foreground/80">{fmtJson(
								call.arguments
							)}</pre>
					</li>
				{/each}
			</ol>
		{:else if selectedNode === 'handoff'}
			{@render detailHeader(
				'Handoff',
				trace.handoff_target ? `target ${trace.handoff_target}` : 'No target',
				GitBranch
			)}
			{#if trace.handoff_summary}
				<p
					class="rounded-xl border bg-amber-500/5 p-4 text-xs text-amber-300"
					style="border-color:color-mix(in srgb, var(--ds-border) 50%, #f59e0b 50%)"
				>
					{trace.handoff_summary}
				</p>
			{/if}
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

	<footer
		class="pointer-events-none absolute inset-x-0 bottom-0 flex justify-center px-6 pb-2 text-[10px] text-muted-foreground/60"
	>
		<div
			class="flex items-center gap-2 rounded-full border bg-[var(--surface)]/90 px-3 py-1 backdrop-blur-sm"
			style="border-color:var(--ds-border)"
		>
			<span class="font-mono text-primary">#{metadata.run_id.slice(0, 8)}</span>
			<span class="opacity-50">·</span>
			<span class="text-primary">{fmtMs(trace.duration_ms)}</span>
			<span class="opacity-50">·</span>
			<span class="text-primary">{trace.model ?? '?'}</span>
			<span class="opacity-50">·</span>
			<span class="text-primary">{trace.ai_provider ?? '?'}</span>
			<span class="opacity-50">·</span>
			<span class="text-primary">{new Date(metadata.created_at).toLocaleString('pt-BR')}</span>
		</div>
	</footer>
</div>

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
