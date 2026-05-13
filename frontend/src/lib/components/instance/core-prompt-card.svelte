<script lang="ts">
	import { Textarea } from '$lib/components/ui/textarea/index.js';

	let { core_prompt = $bindable() }: { core_prompt: string } = $props();
</script>

<div
	class="space-y-3 rounded-none p-6"
	style="background:var(--surface);border:1px solid var(--ds-border)"
>
	<div>
		<h2 class="font-display text-sm font-semibold" style="color:var(--text-main)">Instructions</h2>
		<p class="mt-1 text-xs text-muted-foreground">
			Base behavior for this agent. Topic-specific blocks live in the Instructions tab.
		</p>
	</div>
	<label class="block text-[11px] font-semibold tracking-widest text-muted-foreground uppercase"
		>Core prompt *</label
	>
	<Textarea
		bind:value={core_prompt}
		rows={10}
		class="resize-y font-mono leading-relaxed"
		placeholder="You are..."
	/>
</div>
