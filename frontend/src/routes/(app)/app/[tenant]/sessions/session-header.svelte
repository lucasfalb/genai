<script lang="ts">
	import Clock from '@lucide/svelte/icons/clock';
	import MonitorSmartphone from '@lucide/svelte/icons/monitor-smartphone';
	import { Badge } from '$lib/components/ui/badge/index.js';
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

	const envItems = $derived(environmentMetaItems(session));
	const agentName = $derived(sessionAgent(session, instanceNames));
	const started = $derived(session ? fmtCompactDatetime(session.started_at) : null);
	const lastActivity = $derived(
		session?.last_message_at ? fmtCompactDatetime(session.last_message_at) : null
	);
</script>

<div
	class="glass-panel flex min-h-28 shrink-0 flex-col justify-center gap-1.5 border-b px-6 py-4"
	style="border-color:var(--ds-border)"
>
	{#if session}
		<!-- Row 1: title + live · channel + messages -->
		<div class="flex items-center justify-between gap-3">
			<div class="flex min-w-0 items-center gap-2">
				<h2 class="truncate font-display text-sm font-semibold" style="color:var(--text-main)">
					{sessionTitle(session, instanceNames, selectedSessionId)}
				</h2>
				{#if isLiveSession(session)}
					<Badge
						class="shrink-0 border-emerald-500/20 bg-emerald-500/10 text-[10px] text-emerald-500 hover:bg-emerald-500/10"
					>
						Live
					</Badge>
				{/if}
			</div>
			<div class="flex shrink-0 items-center gap-1.5">
				<Badge variant="outline" class="font-mono text-[10px]">{session.channel}</Badge>
				<Badge variant="outline" class="text-[10px]">{session.message_count} msg</Badge>
			</div>
		</div>

		<!-- Row 2: session ID + agent (left) · timestamps (right) -->
		<div class="flex items-center justify-between gap-4 text-xs text-muted-foreground">
			<div class="flex min-w-0 items-center gap-1.5">
				<code
					class="shrink-0 rounded px-1 py-0.5 font-mono text-[10px] leading-none"
					style="background:color-mix(in srgb,var(--text-main) 6%,transparent);color:var(--text-main)"
				>
					{shortId(session.id)}
				</code>
				<span class="opacity-30">·</span>
				<span class="truncate">{agentName}</span>
			</div>
			{#if started}
				<div class="flex shrink-0 items-center gap-1.5">
					<Clock class="h-3 w-3 opacity-50" />
					<span>{started}</span>
					{#if lastActivity && lastActivity !== started}
						<span class="opacity-30">→</span>
						<span>{lastActivity}</span>
					{/if}
				</div>
			{/if}
		</div>

		<!-- Row 3: environment (only if present) -->
		{#if envItems.length > 0}
			<div class="flex min-w-0 items-center gap-1.5 text-xs" style="color:var(--text-muted);opacity:0.7">
				<MonitorSmartphone class="h-3 w-3 shrink-0" />
				{#each envItems as item, index}
					{#if index > 0}
						<span class="opacity-40">·</span>
					{/if}
					<span class="max-w-40 truncate">{item}</span>
				{/each}
			</div>
		{/if}
	{:else}
		<p class="text-xs text-muted-foreground">Select a conversation to inspect messages.</p>
	{/if}
</div>
