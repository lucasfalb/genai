<script lang="ts">
	import Activity from '@lucide/svelte/icons/activity';
	import Clock from '@lucide/svelte/icons/clock';
	import MonitorSmartphone from '@lucide/svelte/icons/monitor-smartphone';
	import User from '@lucide/svelte/icons/user';
	import MessageSquare from '@lucide/svelte/icons/message-square';
	import Hash from '@lucide/svelte/icons/hash';
	import Terminal from '@lucide/svelte/icons/terminal';
	import * as Sheet from '$lib/components/ui/sheet/index.js';
	import RunTracePanel from '$lib/components/instance/run-trace-panel.svelte';
	import { page } from '$app/state';
	import type { SessionListItem } from '$lib/api/types';
	import {
		environmentMetaItems,
		fmtCompactDatetime,
		isLiveSession,
		sessionAgent,
		sessionTitle,
		shortId
	} from './session-format';

	let {
		session,
		selectedSessionId,
		instanceNames
	}: {
		session: SessionListItem | null;
		selectedSessionId: string | null;
		instanceNames: Map<string, string>;
	} = $props();
	let sheetOpen = $state(false);

	const envItems = $derived(environmentMetaItems(session));
	const agentName = $derived(sessionAgent(session, instanceNames));
	const started = $derived(session ? fmtCompactDatetime(session.started_at) : null);
	const lastActivity = $derived(
		session?.last_message_at ? fmtCompactDatetime(session.last_message_at) : null
	);
</script>

<div
	class="glass-panel flex h-[112px] shrink-0 flex-col justify-between border-b px-5 py-3 select-none"
	style="border-color: var(--ds-border);"
>
	{#if session}
		<!-- ROW 1: Customer Identity + Real-time Status -->
		<div class="flex min-w-0 items-center gap-2">
			<h2 class="truncate text-sm font-bold tracking-tight" style="color: var(--text-main)">
				{sessionTitle(session, instanceNames, selectedSessionId)}
			</h2>

			{#if isLiveSession(session)}
				<span
					class="inline-flex items-center gap-1 rounded border border-emerald-500/20 bg-emerald-500/10 px-1.5 py-0.5 text-[11px] font-semibold text-foreground"
				>
					<span class="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500"></span>
					Live
				</span>
			{/if}

			<span
				class="ml-auto inline-flex items-center gap-1 rounded bg-muted px-1.5 py-0.5 text-[11px] font-bold tracking-wider text-foreground uppercase"
				style="color: var(--text-main)"
			>
				<Hash class="h-3 w-3 shrink-0" />
				{session.channel}
			</span>

			<button
				type="button"
				onclick={() => (sheetOpen = true)}
				class="flex shrink-0 items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-bold tracking-wider text-purple-400 uppercase transition hover:bg-purple-500/10"
			>
				<Activity class="h-3 w-3 shrink-0" />
				Tracing
			</button>
		</div>

		<!-- ROW 2: Assigned Agent + Message Counter -->
		<div class="flex items-center gap-3 text-xs" style="color: var(--text-main)">
			<div class="flex min-w-0 items-center gap-1">
				<User class="h-3.5 w-3.5 shrink-0" />
				<span class="font-medium">Agent:</span>
				<a
					href="/app/{page.params.tenant}/instances/{session.instance_id}"
					class="truncate font-bold underline-offset-2 hover:underline"
					style="color:var(--text-main)">{agentName || 'None'}</a
				>
			</div>

			<span class="font-bold">•</span>

			<div class="flex shrink-0 items-center gap-1">
				<MessageSquare class="h-3.5 w-3.5 shrink-0" />
				<span class="font-bold">{session.message_count}</span>
				<span class="font-medium">messages</span>
			</div>
		</div>

		<!-- ROW 3: Timeline / Activity History -->
		<div class="flex items-center gap-1.5 text-xs" style="color: var(--text-main)">
			{#if started}
				<div class="flex items-center gap-1 font-mono text-[11px]">
					<Clock class="h-3.5 w-3.5 shrink-0" />
					<span>{started}</span>
					{#if lastActivity && lastActivity !== started}
						<span class="font-sans font-bold">→</span>
						<span class="font-medium">{lastActivity}</span>
					{/if}
				</div>
			{/if}
		</div>

		<!-- ROW 4: Technical Footer (Identification ID and System Details) -->
		<div
			class="flex items-center gap-3 truncate border-t pt-1 text-[11px]"
			style="border-color: var(--ds-border); color: var(--text-main);"
		>
			<div class="flex items-center gap-1 font-mono">
				<Terminal class="h-3 w-3 shrink-0" />
				<code class="font-medium">#{shortId(session.id)}</code>
			</div>

			{#if envItems.length > 0}
				<span class="font-bold">•</span>
				<div class="flex items-center gap-1 truncate">
					<MonitorSmartphone class="h-3 w-3 shrink-0" />
					<span class="truncate font-medium">{envItems.join(' · ')}</span>
				</div>
			{/if}
		</div>
	{:else}
		<!-- EMPTY STATE -->
		<div class="flex h-full flex-col justify-center gap-0.5 text-left">
			<p class="text-sm font-bold" style="color: var(--text-main)">No conversation selected</p>
			<p class="text-xs font-medium" style="color: var(--text-main)">
				Select a conversation to inspect messages.
			</p>
		</div>
	{/if}
</div>

{#if session}
	<Sheet.Root bind:open={sheetOpen}>
		<Sheet.Portal>
			<Sheet.Overlay />
			<Sheet.Content side="right" class="w-3/4 p-0">
				<Sheet.Header class="border-b px-5 py-3.5" style="border-color:var(--ds-border)">
					<div class="flex items-center gap-2">
						<Activity class="h-4 w-4 text-purple-400" />
						<Sheet.Title class="text-sm font-semibold">Tracing</Sheet.Title>
						<span class="font-mono text-[10px] text-muted-foreground">
							#{shortId(session.id)}
						</span>
					</div>
				</Sheet.Header>
				<div class="h-full overflow-hidden">
					<RunTracePanel instanceId={session.instance_id} sessionId={session.id} />
				</div>
			</Sheet.Content>
		</Sheet.Portal>
	</Sheet.Root>
{/if}
