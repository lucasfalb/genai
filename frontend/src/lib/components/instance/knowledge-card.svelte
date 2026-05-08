<script lang="ts">
	import Database from '@lucide/svelte/icons/database';
	import { Button } from '$lib/components/ui/button/index.js';
	import KnowledgeDialog from './knowledge-dialog.svelte';

	let { collectionsBaseHref }: { collectionsBaseHref: string } = $props();

	let open = $state(false);
</script>

<div class="rounded-xl p-6" style="background:var(--surface);border:1px solid var(--ds-border)">
	<div class="flex items-center justify-between gap-4">
		<div class="flex items-center gap-3">
			<div class="flex size-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
				<Database class="size-5" />
			</div>
			<div>
				<h2 class="font-display text-sm font-semibold" style="color:var(--text-main)">Knowledge</h2>
				<p class="mt-1 text-sm text-muted-foreground">Add data, files and collections to improve agent responses.</p>
			</div>
		</div>
		<Button variant="outline" onclick={() => (open = true)}>Manage Collections</Button>
	</div>
</div>

<KnowledgeDialog bind:open {collectionsBaseHref} />
