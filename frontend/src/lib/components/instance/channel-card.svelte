<script lang="ts">
	import type { Component, Snippet } from 'svelte';
	import { untrack } from 'svelte';
	import * as Accordion from '$lib/components/ui/accordion/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';

	let {
		icon,
		name,
		description,
		enabled = $bindable(false),
		comingSoon = false,
		ontoggle,
		children
	}: {
		icon: Component;
		name: string;
		description: string;
		enabled?: boolean;
		comingSoon?: boolean;
		ontoggle?: (enabled: boolean) => void;
		children?: Snippet;
	} = $props();

	// Auto-expand when the channel is first enabled; user can collapse at any time.
	let openSections = $state<string[]>([]);

	$effect(() => {
		if (enabled && children && !comingSoon) {
			// Only auto-open; never force-collapse — user controls it from here.
			untrack(() => {
				if (openSections.length === 0) openSections = [name];
			});
		}
	});

	function handleToggle(checked: boolean) {
		enabled = checked;
		ontoggle?.(checked);
	}

	const Icon = icon;
</script>

<div
	class="rounded-xl overflow-hidden"
	style="background:var(--surface);border:1px solid var(--ds-border);opacity:{comingSoon ? 0.6 : 1}"
>
	<Accordion.Root type="multiple" bind:value={openSections}>
		<Accordion.Item value={name} class="border-none">
			<div class="flex items-start justify-between gap-3 px-5 py-4">
				<!-- Left: icon + text -->
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
						<p class="mt-0.5 text-xs text-muted-foreground">{description}</p>
					</div>
				</div>

				<!-- Right: accordion trigger + switch -->
				{#if !comingSoon}
					<div class="flex shrink-0 items-center gap-1 pt-0.5">
						{#if children}
							<Accordion.Trigger
								class="hover:no-underline p-1.5 [&>svg]:size-4 [&>svg]:text-muted-foreground [&>svg]:transition-transform"
							/>
						{/if}
						<!-- stopPropagation so clicking the switch doesn't also trigger the accordion -->
						<div onclick={(e) => e.stopPropagation()} role="none">
							<Switch checked={enabled} onCheckedChange={handleToggle} disabled={comingSoon} />
						</div>
					</div>
				{/if}
			</div>

			{#if children && !comingSoon}
				<Accordion.Content>
					<div class="border-t px-5 py-4" style="border-color:var(--ds-border);background:var(--surface-hover)">
						{@render children()}
					</div>
				</Accordion.Content>
			{/if}
		</Accordion.Item>
	</Accordion.Root>
</div>
