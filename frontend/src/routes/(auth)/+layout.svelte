<script lang="ts">
	import '../layout.css';
	import { page } from '$app/state';
	import { fly } from 'svelte/transition';
	import { ModeWatcher } from 'mode-watcher';
	import ModeToggle from '$lib/components/mode-toggle.svelte';
	import Bot from '@lucide/svelte/icons/bot';
	import HeroCanvas from '$lib/components/hero-canvas.svelte';

	let { data, children } = $props();
	const platformName = $derived(data.publicSettings.platform_name || 'GENAI');
</script>

<svelte:head>
	<title>{platformName}</title>
</svelte:head>

<ModeWatcher defaultMode="dark" />

<div
	class="relative z-10 flex h-screen overflow-hidden font-sans selection:bg-blue-500/30"
	style="background:var(--canvas);color:var(--text-main)"
>
	<!-- ── HERO SIDE ─────────────────────────────────────────── -->
	<div class="relative hidden w-1/2 flex-col overflow-hidden border-r lg:flex">
		<!-- WebGL metaball animation -->
		<HeroCanvas />
	</div>

	<!-- ── FORM SIDE ─────────────────────────────────────────── -->
	<div class="relative flex flex-1 flex-col overflow-y-auto">
		<!-- Vignette -->
		<div
			class="pointer-events-none absolute inset-0"
			style="background:radial-gradient(ellipse 85% 80% at 50% 50%,transparent 15%,color-mix(in srgb,var(--canvas) 85%,transparent) 100%);z-index:1"
		></div>

		<!-- Top bar -->
		<div class="relative flex h-14 shrink-0 items-center justify-between px-6" style="z-index:2">
			<a href="/login" class="flex items-center gap-2 lg:invisible">
				<Bot class="size-5 text-blue-500" />
				<span
					class="font-display text-base font-semibold tracking-tight"
					style="color:var(--text-main)">{platformName}</span
				>
			</a>
			<ModeToggle />
		</div>

		<!-- Form area -->
		<div
			class="relative flex flex-1 items-center justify-center px-6 py-8 lg:px-12"
			style="z-index:2"
		>
			<div class="w-full max-w-[400px]">
				{#key page.url.pathname}
					<div in:fly={{ y: 16, duration: 280, opacity: 0 }}>
						{@render children()}
					</div>
				{/key}
			</div>
		</div>
	</div>
</div>
