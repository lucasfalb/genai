<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { navigating } from '$app/state';
	import { beforeNavigate, afterNavigate } from '$app/navigation';
	import { ModeWatcher } from 'mode-watcher';
	import { Toaster } from '$lib/components/ui/sonner';

	let { children } = $props();
	const isNavigating = $derived(Boolean(navigating.to));

	let navStart = 0;
	let navFrom = '';

	beforeNavigate(({ from, to }) => {
		navStart = performance.now();
		navFrom = from?.url.pathname ?? '';
		console.log(`[nav] → ${to?.url.pathname ?? '?'} iniciando...`);
	});

	afterNavigate(({ to, type }) => {
		if (!navStart) return; // ignora load inicial
		const elapsed = Math.round(performance.now() - navStart);
		const dest = to?.url.pathname ?? '?';
		const label = elapsed < 300 ? '✓' : elapsed < 800 ? '⚠' : '✗';
		console.log(`[nav] ${label} ${navFrom} → ${dest}  ${elapsed}ms  (${type})`);
		navStart = 0;
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<ModeWatcher defaultMode="dark" />
<Toaster richColors closeButton position="top-right" />
<div class:active={isNavigating} class="page-transition-line" aria-hidden="true"></div>

{@render children()}
