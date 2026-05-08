<script lang="ts">
	import Activity from '@lucide/svelte/icons/activity';
</script>

<div class="mx-auto max-w-5xl space-y-6 p-6">
	<div class="flex items-center gap-3">
		<div class="flex size-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
			<Activity class="size-5" />
		</div>
		<div>
			<h1 class="font-display text-xl font-semibold" style="color:var(--text-main)">Observability</h1>
			<p class="mt-1 text-sm text-muted-foreground">Tenant execution logs, traces and agent activity will be surfaced here.</p>
		</div>
	</div>

	<section class="rounded-xl p-6" style="background:var(--surface);border:1px solid var(--ds-border)">
		<p class="text-sm text-muted-foreground">No activity stream is available yet. Backend audit and run traces are already tenant-scoped; the frontend timeline can be attached when the observability API is exposed.</p>
	</section>
</div>
