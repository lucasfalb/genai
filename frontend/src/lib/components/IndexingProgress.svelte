<script lang="ts">
	import { Progress } from '$lib/components/ui/progress/index.js';
	import CircularProgress from '$lib/components/CircularProgress.svelte';

	let {
		status,
		chunkCount = 0
	}: {
		status: string;
		chunkCount?: number;
	} = $props();

	const statusConfig = {
		uploaded: { color: 'text-blue-400', label: 'Queued' },
		indexing: { color: 'text-yellow-400', label: 'Indexing' },
		indexed: { color: 'text-emerald-400', label: 'Indexed' },
		failed: { color: 'text-red-400', label: 'Failed' }
	};

	const config = $derived(statusConfig[status as keyof typeof statusConfig] || statusConfig.uploaded);
	const progress = $derived(
		status === 'indexed' ? 100 :
		status === 'indexing' ? 66 :
		status === 'uploaded' ? 33 :
		0
	);
</script>

<div class="flex items-center gap-2 min-w-[200px]">
	<div class="flex items-center gap-1.5 min-w-[100px]">
		<CircularProgress {status} size={16} />
		<span class="text-xs font-medium {config.color}">
			{config.label}
		</span>
	</div>
	<div class="flex-1">
		<Progress value={progress} class="h-1.5" />
	</div>
	{#if status === 'indexed' && chunkCount > 0}
		<span class="text-[10px] text-muted-foreground font-mono">
			{chunkCount} chunks
		</span>
	{/if}
</div>
