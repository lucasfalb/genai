<script lang="ts">
	import Filter from '@lucide/svelte/icons/filter';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Search from '@lucide/svelte/icons/search';
	import X from '@lucide/svelte/icons/x';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import type { SessionListItem } from '$lib/api/types';
	import {
		fmtTime,
		isLiveSession,
		sessionAgent,
		sessionInitial,
		sessionTitle
	} from './session-format';

	let {
		sessions,
		selectedSessionId,
		instanceNames,
		loading,
		loadingMore,
		hasActiveFilters,
		activeFilterCount,
		searchTerm = $bindable(''),
		sentinel = $bindable(null),
		openFilters,
		clearFilters,
		refresh,
		selectSession
	}: {
		sessions: SessionListItem[];
		selectedSessionId: string | null;
		instanceNames: Map<string, string>;
		loading: boolean;
		loadingMore: boolean;
		hasActiveFilters: boolean;
		activeFilterCount: number;
		searchTerm: string;
		sentinel: HTMLDivElement | null;
		openFilters: () => void;
		clearFilters: () => void;
		refresh: () => void;
		selectSession: (session: SessionListItem) => void;
	} = $props();
</script>

<aside
	class="flex min-h-0 w-full shrink-0 flex-col border-b glass-panel lg:w-[360px] lg:border-r lg:border-b-0"
	style="border-color:var(--ds-border)"
>
	<div class="space-y-3 border-b bg-transparent p-3.5" style="border-color:var(--ds-border)">
		<div class="flex items-center gap-2">
			<div class="relative min-w-0 flex-1">
				<Search class="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
				<Input
					class="h-9 bg-background pl-9"
					placeholder="Search conversations..."
					bind:value={searchTerm}
					aria-label="Search sessions"
				/>
			</div>
			<Button
				variant="outline"
				size="icon"
				class="h-9 w-9 shrink-0 bg-background"
				onclick={refresh}
				disabled={loading}
				aria-label="Refresh sessions"
			>
				<RefreshCw class="h-4 w-4 {loading ? 'animate-spin' : ''}" />
			</Button>
		</div>

		<div class="flex min-w-0 items-center gap-2">
			<Button
				variant="outline"
				size="sm"
				class="h-9 w-full min-w-0 flex-1 justify-start gap-2 bg-background px-3"
				onclick={openFilters}
			>
				<Filter class="h-4 w-4 shrink-0" />
				<span class="truncate">Advanced filters</span>
				{#if activeFilterCount > 0}
					<Badge variant="outline" class="ml-auto h-5 shrink-0 px-1.5 text-[10px]">
						{activeFilterCount}
					</Badge>
				{/if}
			</Button>
			{#if hasActiveFilters}
				<Button
					variant="ghost"
					size="icon"
					class="h-9 w-9 shrink-0 border bg-background text-muted-foreground hover:bg-muted/50"
					onclick={clearFilters}
					aria-label="Clear filters"
				>
					<X class="h-4 w-4" />
				</Button>
			{/if}
		</div>
	</div>

	<div class="min-h-0 flex-1 overflow-y-auto p-2">
		{#if loading && sessions.length === 0}
			<div class="px-3 py-10 text-center text-sm text-muted-foreground">Loading sessions...</div>
		{:else if sessions.length === 0}
			<div class="px-3 py-10 text-center text-sm text-muted-foreground">
				{hasActiveFilters ? 'No sessions match the current filters.' : 'No sessions found.'}
			</div>
		{:else}
			<div class="space-y-1">
				{#each sessions as session (session.id)}
					<button
						type="button"
						class="w-full border border-transparent p-3 text-left transition focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none {selectedSessionId === session.id ? 'bg-sidebar-accent text-sidebar-accent-foreground active:text-sidebar-accent-foreground' : ''}"
						style={selectedSessionId === session.id
							? 'border-color:var(--ds-border-hover)'
							: 'background:transparent'}
						onclick={() => selectSession(session)}
					>
						<div class="flex items-start gap-3">
							<div
								class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border bg-background text-xs font-semibold"
								style="border-color:var(--ds-border)"
							>
								{sessionInitial(session, instanceNames)}
							</div>
							<div class="min-w-0 flex-1">
								<div class="flex items-start justify-between gap-2">
									<div class="min-w-0">
										<div class="truncate text-sm font-semibold">
											{sessionTitle(session, instanceNames)}
										</div>
										<div class="truncate text-xs text-muted-foreground">
											{sessionAgent(session, instanceNames)}
										</div>
									</div>
									<div class="shrink-0 text-xs text-muted-foreground">
										{fmtTime(session.last_message_at ?? session.started_at)}
									</div>
								</div>
								<div class="mt-2 flex flex-wrap items-center gap-1.5">
									{#if isLiveSession(session)}
										<Badge
											class="border-emerald-500/20 bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/10"
										>
											Live
										</Badge>
									{/if}
									<Badge variant="outline" class="text-[11px]">{session.channel}</Badge>
									<span class="text-xs text-muted-foreground">{session.message_count} messages</span
									>
								</div>
							</div>
						</div>
					</button>
				{/each}
			</div>
		{/if}

		<div bind:this={sentinel} class="h-1"></div>

		{#if loadingMore}
			<div class="py-4 text-center text-sm text-muted-foreground">Loading more...</div>
		{/if}
	</div>
</aside>
