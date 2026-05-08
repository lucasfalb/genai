<script lang="ts">
	import type { Component, Snippet } from 'svelte';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';

	let {
		icon,
		name,
		description,
		enabled = $bindable(false),
		comingSoon = false,
		children
	}: {
		icon: Component;
		name: string;
		description: string;
		enabled?: boolean;
		comingSoon?: boolean;
		children?: Snippet;
	} = $props();

	const Icon = icon;
</script>

<div
	class="rounded-xl transition-colors overflow-hidden"
	style="background:var(--surface);border:1px solid var(--ds-border);opacity:{comingSoon ? 0.6 : 1}"
>
	<div class="flex items-start justify-between gap-3 p-5">
		<div class="flex min-w-0 items-start gap-3">
			<div class="flex size-10 shrink-0 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
				<Icon class="size-5" />
			</div>
			<div class="min-w-0">
				<div class="flex items-center gap-2">
					<h3 class="font-display text-sm font-semibold" style="color:var(--text-main)">{name}</h3>
					{#if comingSoon}
						<Badge variant="outline" class="text-[10px]">Coming soon</Badge>
					{:else if enabled}
						<Badge variant="default" class="text-[10px]">Active</Badge>
					{/if}
				</div>
				<p class="mt-1 text-xs text-muted-foreground">{description}</p>
			</div>
		</div>
		<div class="flex shrink-0 items-center gap-2">
			{#if !comingSoon}
				{#if enabled && children}
					<ChevronDown class="size-4 text-muted-foreground transition-transform" />
				{/if}
				<Switch bind:checked={enabled} />
			{/if}
		</div>
	</div>

	{#if enabled && !comingSoon && children}
		<div class="border-t px-5 py-4" style="border-color:var(--ds-border);background:var(--surface-hover)">
			{@render children()}
		</div>
	{/if}
</div>
