<script lang="ts">
	import ProgressCircle from './ProgressCircle.svelte';

	let { status, progress = 0 } = $props<{ status: string; progress?: number }>();

	const LABELS: Record<string, string> = {
		empty: 'Empty',
		indexing: 'Indexing',
		ready: 'Ready',
		partial: 'Partial',
		failed: 'Failed'
	};

	const CLASSES: Record<string, string> = {
		empty: 'bg-zinc-500/10 text-zinc-400',
		indexing: 'bg-blue-500/10 text-blue-400',
		ready: 'bg-emerald-500/10 text-emerald-400',
		partial: 'bg-amber-500/10 text-amber-400',
		failed: 'bg-red-500/10 text-red-400'
	};
</script>

<div class="inline-flex items-center gap-2">
	<ProgressCircle {status} {progress} size={20} />
	<div class="inline-flex flex-col gap-0.5">
		<span class="w-fit rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider {CLASSES[status] ?? CLASSES.empty}">
			{LABELS[status] ?? status}
		</span>
		{#if status === 'indexing'}
			<span class="text-[9px] text-muted-foreground">{Math.round((progress ?? 0) * 100)}%</span>
		{/if}
	</div>
</div>
