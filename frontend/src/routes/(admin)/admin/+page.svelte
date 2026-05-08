<script lang="ts">
	let { data } = $props();
</script>

<div class="min-h-screen bg-background p-8" style="color:var(--text-main)">
	<div class="mx-auto max-w-5xl space-y-4">
		<p class="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Superadmin</p>
		<h1 class="font-display text-2xl font-semibold">Platform Administration</h1>
		<p class="text-sm text-muted-foreground">
			Global platform management for {data.user.email}. Tenant-scoped user workspaces live under
			<code class="rounded bg-white/5 px-1.5 py-0.5">/app/&lbrace;tenant&rbrace;</code>.
		</p>
	</div>
</div>
