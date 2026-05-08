<script lang="ts">
	let { status }: { status: string } = $props();

	const labels: Record<string, string> = {
		active: 'Active',
		inactive: 'Inactive',
		pending: 'Pending',
		suspended: 'Suspended',
		accepted: 'Accepted',
		expired: 'Expired',
		cancelled: 'Cancelled'
	};

	const classes: Record<string, string> = {
		active: 'bg-emerald-500/10 text-emerald-400',
		accepted: 'bg-emerald-500/10 text-emerald-400',
		inactive: 'bg-white/5 text-muted-foreground',
		pending: 'bg-amber-500/10 text-amber-400',
		suspended: 'bg-red-500/10 text-red-400',
		expired: 'bg-red-500/10 text-red-400',
		cancelled: 'bg-white/5 text-muted-foreground'
	};
</script>

<span class="rounded-full px-2 py-1 text-[10px] font-semibold uppercase {classes[status] ?? 'bg-white/5 text-muted-foreground'}">
	{labels[status] ?? status}
</span>
