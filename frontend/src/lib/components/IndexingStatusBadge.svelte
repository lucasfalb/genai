<script lang="ts">
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

	const percent = $derived(Math.max(0, Math.min(100, Math.round((progress ?? 0) * 100))));
</script>

<div class="inline-flex flex-col gap-1">
	<span class="w-fit rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider {CLASSES[status] ?? CLASSES.empty}">
		{LABELS[status] ?? status}
	</span>
	{#if status === 'indexing'}
		<div class="h-1.5 w-24 overflow-hidden rounded-full bg-white/10">
			<div class="h-full rounded-full bg-blue-500 transition-all" style={`width:${percent}%`}></div>
		</div>
	{/if}
</div>
