<script lang="ts">
	let {
		status,
		size = 20
	}: {
		status: string;
		size?: number;
	} = $props();

	const radius = 8;
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
			? '#10b981' // emerald-400
			: status === 'indexing'
				? '#fbbf24' // yellow-400
				: status === 'uploaded'
					? '#60a5fa' // blue-400
					: status === 'failed'
						? '#f87171' // red-400
						: '#9ca3af' // gray-400
	);
</script>

<svg width={size} height={size} class="circular-progress">
	<!-- Background circle -->
	<circle
		cx={size / 2}
		cy={size / 2}
		r={radius}
		fill="none"
		stroke="currentColor"
		stroke-width="2"
		class="opacity-20"
	/>
	<!-- Progress circle -->
	<circle
		cx={size / 2}
		cy={size / 2}
		r={radius}
		fill="none"
		stroke={color}
		stroke-width="2"
		stroke-dasharray={circumference}
		stroke-dashoffset={strokeDashoffset}
		stroke-linecap="round"
		class="progress-ring"
		style="transform: rotate(-90deg); transform-origin: 50% 50%;"
	/>
	{#if status === 'indexed'}
		<!-- Checkmark for completed -->
		<path
			d="M {size * 0.3} {size * 0.5} L {size * 0.45} {size * 0.65} L {size * 0.7} {size * 0.35}"
			stroke={color}
			stroke-width="2"
			fill="none"
			stroke-linecap="round"
			stroke-linejoin="round"
		/>
	{:else if status === 'failed'}
		<!-- X for failed -->
		<g stroke={color} stroke-width="2" stroke-linecap="round">
			<line x1={size * 0.35} y1={size * 0.35} x2={size * 0.65} y2={size * 0.65} />
			<line x1={size * 0.65} y1={size * 0.35} x2={size * 0.35} y2={size * 0.65} />
		</g>
	{/if}
</svg>

<style>
	.circular-progress {
		display: inline-block;
	}

	.progress-ring {
		transition: stroke-dashoffset 0.5s ease-in-out;
	}
</style>
