<script lang="ts">
	import { Input } from '$lib/components/ui/input/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import Copy from '@lucide/svelte/icons/copy';
	import { toast } from 'svelte-sonner';

	let { instanceId }: { instanceId: string } = $props();

	let title = $state('Chat with us');
	let primaryColor = $state('#3b82f6');
	let allowedDomains = $state('');

	const snippet = $derived(`<script src="https://cdn.example.com/widget.js" data-instance="${instanceId}"><\/script>`);

	function copy() {
		navigator.clipboard.writeText(snippet);
		toast.success('Snippet copied.');
	}
</script>

<div class="space-y-4">
	<div class="grid gap-3 md:grid-cols-2">
		<div class="space-y-1.5">
			<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Widget title</label>
			<Input bind:value={title} placeholder="Chat with us" />
		</div>
		<div class="space-y-1.5">
			<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Primary color</label>
			<Input type="color" bind:value={primaryColor} class="w-full" />
		</div>
	</div>

	<div class="space-y-1.5">
		<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Allowed domains</label>
		<Textarea bind:value={allowedDomains} rows={2} placeholder="example.com, app.example.com" class="font-mono text-xs" />
	</div>

	<div class="space-y-1.5">
		<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Embed snippet</label>
		<div class="flex items-start gap-2">
			<pre class="flex-1 overflow-x-auto rounded border bg-[var(--canvas)] p-3 text-[11px] font-mono" style="border-color:var(--ds-border)">{snippet}</pre>
			<Button variant="outline" size="icon-sm" onclick={copy}>
				<Copy />
			</Button>
		</div>
	</div>
</div>
