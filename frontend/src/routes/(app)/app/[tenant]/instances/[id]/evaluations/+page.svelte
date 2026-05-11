<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import Clock from '@lucide/svelte/icons/clock';
	import RefreshCcw from '@lucide/svelte/icons/refresh-ccw';
	import MessagesSquare from '@lucide/svelte/icons/messages-square';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import { tracesApi } from '$lib/api/chat';
	import { getErrorMessage } from '$lib/api/client';
	import type { RunTraceListItem } from '$lib/api/types';

	let { data } = $props();

	let items = $state<RunTraceListItem[]>([]);
	let loading = $state(false);
	let error = $state('');

	type SessionRow = {
		sessionId: string;
		runCount: number;
		firstRunAt: string;
		lastRunAt: string;
		latestPreview: string | null;
	};

	let sessionList = $derived.by<SessionRow[]>(() => {
		const map = new Map<string, RunTraceListItem[]>();
		for (const item of items) {
			const list = map.get(item.session_id) ?? [];
			list.push(item);
			map.set(item.session_id, list);
		}
		const sessions: SessionRow[] = [];
		for (const [sessionId, runs] of map) {
			runs.sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());
			sessions.push({
				sessionId,
				runCount: runs.length,
				firstRunAt: runs[runs.length - 1].started_at,
				lastRunAt: runs[0].started_at,
				latestPreview: runs[0].final_response_preview ?? null
			});
		}
		sessions.sort((a, b) => new Date(b.lastRunAt).getTime() - new Date(a.lastRunAt).getTime());
		return sessions;
	});

	onMount(load);

	async function load(): Promise<void> {
		loading = true;
		error = '';
		try {
			items = await tracesApi.list(data.instance.id, undefined, 100);
		} catch (err) {
			error = getErrorMessage(err, 'Failed to list evaluations.');
			items = [];
		} finally {
			loading = false;
		}
	}

	async function selectSession(sessionId: string) {
		await goto(`./evaluations/${sessionId}`);
	}

	function fmtPeriod(first: string, last: string): string {
		const a = new Date(first);
		const b = new Date(last);
		const fmt = (d: Date) =>
			d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }) +
			' ' +
			d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
		return `${fmt(a)} → ${fmt(b)}`;
	}

	function fmtFull(value: string): string {
		return new Date(value).toLocaleString('pt-BR');
	}
</script>

<div class="flex h-full flex-col overflow-hidden">
	<header
		class="flex items-center justify-between border-b px-6 py-4"
		style="border-color:var(--ds-border);background:var(--surface)"
	>
		<div class="flex items-center gap-3">
			<div
				class="flex size-9 items-center justify-center rounded-lg"
				style="background:color-mix(in srgb,#a855f7 15%,transparent);border:1px solid color-mix(in srgb,#a855f7 30%,transparent)"
			>
				<Clock class="size-4 text-purple-400" />
			</div>
			<div>
				<h2 class="text-sm leading-tight font-semibold" style="color:var(--text-main)">
					Evaluations
				</h2>
				<p class="text-[11px] text-muted-foreground">
					{sessionList.length} session{sessionList.length !== 1 ? 's' : ''} · click to inspect
				</p>
			</div>
		</div>
		<Button variant="outline" size="sm" onclick={load} disabled={loading}>
			{#if loading}
				<Spinner class="size-3.5" />
			{:else}
				<RefreshCcw class="size-3.5" />
			{/if}
			Refresh
		</Button>
	</header>

	<div class="flex-1 overflow-y-auto">
		{#if loading && items.length === 0}
			<div class="flex h-full items-center justify-center text-sm text-muted-foreground">
				<Spinner class="mr-2 size-4" />
				Loading…
			</div>
		{:else if error}
			<div class="flex h-full items-center justify-center px-6">
				<div
					class="max-w-md rounded-xl border bg-[var(--canvas)] p-6 text-center text-sm text-red-400"
					style="border-color:var(--ds-border)"
				>
					{error}
				</div>
			</div>
		{:else if items.length === 0}
			<div class="flex h-full items-center justify-center px-6 text-center">
				<div class="max-w-sm">
					<Clock class="mx-auto mb-3 size-8 text-muted-foreground" />
					<p class="text-sm text-muted-foreground">No runs executed in this instance yet.</p>
				</div>
			</div>
		{:else}
			<table class="w-full">
				<thead
					class="sticky top-0 z-10 border-b text-[10px] tracking-wider text-muted-foreground uppercase"
					style="border-color:var(--ds-border);background:var(--surface)"
				>
					<tr>
						<th class="w-[180px] px-6 py-2 text-left font-semibold">Session</th>
						<th class="w-[60px] px-6 py-2 text-right font-semibold">Runs</th>
						<th class="w-[220px] px-6 py-2 text-left font-semibold">Period</th>
						<th class="px-6 py-2 text-left font-semibold">Response</th>
					</tr>
				</thead>
				<tbody>
					{#each sessionList as session (session.sessionId)}
						<tr
							class="cursor-pointer border-b transition-colors hover:bg-[var(--surface-hover)]"
							style="border-color:var(--ds-border)"
							onclick={() => selectSession(session.sessionId)}
						>
							<td class="px-6 py-3">
								<div class="flex items-center gap-2">
									<MessagesSquare class="size-3.5 text-muted-foreground" />
									<span class="font-mono text-[11px] text-muted-foreground">
										#{session.sessionId.slice(0, 8)}
									</span>
								</div>
							</td>
							<td class="px-6 py-3 text-right font-mono text-[11px] text-muted-foreground">
								{session.runCount}
							</td>
							<td class="w-[220px] px-6 py-3">
								<Tooltip.Root>
									<Tooltip.Trigger class="cursor-pointer">
										<span class="font-mono text-[11px] text-muted-foreground">
											{fmtPeriod(session.firstRunAt, session.lastRunAt)}
										</span>
									</Tooltip.Trigger>
									<Tooltip.Content side="bottom" sideOffset={4}>
										<div class="flex flex-col gap-0.5 text-[11px]">
											<span>First: {fmtFull(session.firstRunAt)}</span>
											<span>Last: {fmtFull(session.lastRunAt)}</span>
											<span class="text-[10px] opacity-60"
												>{session.runCount} run{session.runCount !== 1 ? 's' : ''}</span
											>
										</div>
									</Tooltip.Content>
								</Tooltip.Root>
							</td>
							<td class="px-6 py-3 text-xs text-foreground/80">
								<span class="line-clamp-2">{session.latestPreview ?? '—'}</span>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</div>
</div>
