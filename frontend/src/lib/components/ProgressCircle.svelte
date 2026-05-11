<script lang="ts">
	let { status, progress = 0, size = 16 }: { status: string; progress?: number; size?: number } = $props();

	const strokeColor: Record<string, string> = {
		uploaded: 'stroke-blue-400',
		indexing: 'stroke-blue-400',
		indexed: 'stroke-emerald-400',
		failed: 'stroke-red-400',
		ready: 'stroke-emerald-400',
		partial: 'stroke-amber-400',
		empty: 'stroke-zinc-400'
	};

	const pct = $derived(Math.round(Math.max(0, Math.min(1, progress)) * 100));
	const r = 14;
	const circ = $derived(2 * Math.PI * r);
	const offset = $derived(circ - (pct / 100) * circ);
	const isIndeterminate = $derived(
		(status === 'uploaded' || status === 'indexing') && pct === 0
	);
	const dashArray = isIndeterminate ? `${circ * 0.6} ${circ * 0.4}` : circ;
</script>

<svg viewBox="0 0 36 36" width={size} height={size} class="shrink-0">
	<circle cx="18" cy="18" r={r} fill="none" class="stroke-white/10" stroke-width="3" />
	<circle
		cx="18"
		cy="18"
		r={r}
		fill="none"
		class={strokeColor[status] ?? 'stroke-zinc-400'}
		class:animate-spin-circle={isIndeterminate}
		stroke-width="3"
		stroke-linecap="round"
		stroke-dasharray={dashArray}
		stroke-dashoffset={isIndeterminate ? circ * 0.75 : offset}
		transform="rotate(-90 18 18)"
		style={isIndeterminate ? `--circ:${circ}` : 'transition: stroke-dashoffset 0.5s ease-in-out'}
	/>
	{#if status === 'indexed' || status === 'ready'}
		<polyline points="12,18 16,22 24,14" fill="none" class="stroke-emerald-400" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
	{:else if status === 'failed'}
		<line x1="13" y1="13" x2="23" y2="23" class="stroke-red-400" stroke-width="2.5" stroke-linecap="round" />
		<line x1="23" y1="13" x2="13" y2="23" class="stroke-red-400" stroke-width="2.5" stroke-linecap="round" />
	{/if}
</svg>

<style>
	.animate-spin-circle {
		animation: spin-dash 1.5s ease-in-out infinite;
	}
	@keyframes spin-dash {
		0% { stroke-dashoffset: calc(var(--circ) * 0.75); }
		50% { stroke-dashoffset: calc(var(--circ) * 0.25); }
		100% { stroke-dashoffset: calc(var(--circ) * 0.75); }
	}
</style>
