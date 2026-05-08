<script lang="ts">
	import Bot from '@lucide/svelte/icons/bot';
	import Plus from '@lucide/svelte/icons/plus';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import { page } from '$app/state';
	import { tenantBaseFromPath } from '$lib/routes/tenant';

	let { data } = $props();
	const instances = $derived(data.instances);
	const appBase = $derived(tenantBaseFromPath(page.url.pathname));

	const STATUS_COLOR: Record<string, string> = {
		active: 'text-emerald-400 bg-emerald-400/10',
		inactive: 'text-zinc-400 bg-zinc-400/10',
		draft: 'text-amber-400 bg-amber-400/10'
	};
</script>

<div class="border-b px-6 py-5" style="border-color:var(--ds-border);background:color-mix(in srgb,var(--surface) 70%,transparent)">
	<div class="flex items-center justify-between gap-4">
		<div>
			<h1 class="font-display text-2xl font-semibold tracking-tight" style="color:var(--text-main)">Agents</h1>
			<p class="mt-1 text-sm text-muted-foreground">Create, test and operate tenant AI agents.</p>
		</div>
		<a href="{appBase}/instances/new" class="inline-flex h-10 items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white transition-colors hover:bg-blue-500">
			<Plus class="h-4 w-4" />
			New Agent
		</a>
	</div>
</div>

<div class="p-6">
	{#if instances.length === 0}
		<div
			class="flex min-h-[420px] flex-col items-center justify-center gap-4 rounded-xl py-16 text-center"
			style="background:var(--surface);border:1px solid var(--ds-border)"
		>
			<div class="flex h-16 w-16 items-center justify-center rounded-2xl" style="background:rgba(59,130,246,0.1);border:1px solid rgba(59,130,246,0.2)">
				<Sparkles class="h-8 w-8 text-blue-400" />
			</div>
			<div>
				<p class="font-display text-lg font-semibold" style="color:var(--text-main)">No agents yet</p>
				<p class="mt-1 max-w-md text-sm text-muted-foreground">Start with a template or create a blank agent connected to your tenant settings.</p>
			</div>
			<a
				href="{appBase}/instances/new"
				class="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-500"
			>
				<Plus class="h-4 w-4" />
				Create Agent
			</a>
		</div>

	{:else}
		<div class="overflow-hidden rounded-xl" style="background:var(--surface);border:1px solid var(--ds-border)">
			{#each instances as inst (inst.id)}
				<a
					href="{appBase}/instances/{inst.id}"
					class="group flex items-center gap-4 border-b px-5 py-4 transition-colors last:border-b-0 hover:bg-white/[0.03]"
					style="border-color:var(--ds-border)"
				>
					<div
						class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl"
						style="background:linear-gradient(135deg,rgba(59,130,246,0.2),rgba(139,92,246,0.15));border:1px solid rgba(59,130,246,0.2)"
					>
						<Bot class="h-5 w-5 text-blue-400" />
					</div>
					<div class="min-w-0 flex-1">
						<p class="truncate text-base font-semibold" style="color:var(--text-main)">{inst.name}</p>
						<p class="truncate text-xs text-muted-foreground">{inst.description || inst.model}</p>
					</div>
					<span
						class="shrink-0 rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider {STATUS_COLOR[inst.status] ?? STATUS_COLOR.inactive}"
					>
						{inst.status}
					</span>
					<ChevronRight class="h-4 w-4 shrink-0 text-muted-foreground/40 transition-transform group-hover:translate-x-0.5" />
				</a>
			{/each}
		</div>
	{/if}
</div>
