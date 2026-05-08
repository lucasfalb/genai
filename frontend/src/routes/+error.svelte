<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Card, CardContent } from '$lib/components/ui/card/index.js';
	import Home from '@lucide/svelte/icons/home';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Bot from '@lucide/svelte/icons/bot';
</script>

<div class="flex min-h-full items-center justify-center px-8 py-16">
	<Card class="relative w-full max-w-md gap-0 overflow-hidden border-dashed p-0">
		<div
			class="pointer-events-none absolute -top-32 -right-32 h-64 w-64 rounded-full bg-blue-600/10 blur-[120px]"
		></div>
		<div
			class="pointer-events-none absolute -bottom-24 -left-24 h-48 w-48 rounded-full bg-cyan-600/5 blur-[100px]"
		></div>

		<CardContent class="relative flex flex-col items-center px-10 py-14 text-center">
			<div
				class="mb-6 flex size-16 items-center justify-center rounded-full"
				style="background:color-mix(in srgb,var(--surface) 60%,transparent);border:1px solid var(--ds-border)"
			>
				<Bot class="size-7 text-blue-500/60" />
			</div>

			<span
				class="font-display text-[7rem] leading-none font-bold tracking-tighter"
				style="color:var(--text-main)"
			>
				<span class="text-blue-500/30">4</span>
				<span class="text-blue-500/50">0</span>
				<span class="text-blue-500/30">4</span>
			</span>

			<h1
				class="mt-4 font-display text-lg font-semibold tracking-tight"
				style="color:var(--text-main)"
			>
				Page not found
			</h1>

			<p class="mt-2 max-w-xs text-sm leading-relaxed" style="color:var(--text-muted)">
				The agent instance or route you're looking for doesn't exist or has been decommissioned.
			</p>

			<div class="mt-8 flex items-center gap-3">
				<Button variant="outline" class="gap-2 px-4 py-2 text-sm" onclick={() => history.back()}>
					<ArrowLeft class="size-4" />
					Go Back
				</Button>
				<Button
					class="gap-2 px-4 py-2 text-sm"
					style="background:var(--text-main);color:var(--canvas);box-shadow:0 0 20px rgba(255,255,255,0.08)"
					onclick={() => goto('/')}
				>
					<Home class="size-4" />
					Dashboard
				</Button>
			</div>

			<span
				class="mt-8 font-mono text-[11px]"
				style="color:color-mix(in srgb,var(--text-muted) 50%,transparent)"
			>
				{$page.status === 404 ? 'Not Found' : `Error {$page.status}`}
			</span>
		</CardContent>
	</Card>
</div>
