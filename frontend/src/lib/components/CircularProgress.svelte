<script lang="ts">
	let {
		status,
		size = 20
	}: {
		status: string;
		size?: number;
	} = $props();

	const VIEWBOX = 36;
	const radius = 16;
	const circumference = 2 * Math.PI * radius;

	const progress = $derived(
		status === 'indexed'
			? 100
			: status === 'indexing'
				? 66
				: status === 'uploaded'
					? 33
					: status === 'failed'
						? 100
						: 0
	);

	const strokeDashoffset = $derived(circumference - (progress / 100) * circumference);

	const color = $derived(
		status === 'indexed'
			? '#10b981'
			: status === 'indexing'
				? '#fbbf24'
				: status === 'uploaded'
					? '#60a5fa'
					: status === 'failed'
						? '#f87171'
						: '#9ca3af'
	);
</script>

<svg
	viewBox="0 0 {VIEWBOX} {VIEWBOX}"
	width={size}
	height={size}
	class="circular-progress shrink-0"
>
	<circle
		cx={VIEWBOX / 2}
		cy={VIEWBOX / 2}
		r={radius}
		fill="none"
		stroke="currentColor"
		stroke-width="3"
		class="opacity-20"
	/>
	<circle
		cx={VIEWBOX / 2}
		cy={VIEWBOX / 2}
		r={radius}
		fill="none"
		stroke={color}
		stroke-width="3"
		stroke-dasharray={circumference}
		stroke-dashoffset={strokeDashoffset}
		stroke-linecap="round"
		class="progress-ring"
		transform="rotate(-90 {VIEWBOX / 2} {VIEWBOX / 2})"
	/>
	{#if status === 'indexed'}
		<polyline
			points="12,18 16,22 24,14"
			fill="none"
			stroke={color}
			stroke-width="3"
			stroke-linecap="round"
			stroke-linejoin="round"
		/>
	{:else if status === 'failed'}
		<g stroke={color} stroke-width="3" stroke-linecap="round">
			<line x1="13" y1="13" x2="23" y2="23" />
			<line x1="23" y1="13" x2="13" y2="23" />
		</g>
	{/if}
</svg>

<style>
	.circular-progress {
		display: inline-block;
		vertical-align: middle;
	}

	.progress-ring {
		transition: stroke-dashoffset 0.5s ease-in-out;
	}
</style>
