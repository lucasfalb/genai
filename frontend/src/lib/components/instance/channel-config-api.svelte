<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import Copy from '@lucide/svelte/icons/copy';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import { toast } from 'svelte-sonner';

	let { instanceId }: { instanceId: string } = $props();

	const endpoint = $derived(`POST /agent/instances/${instanceId}/chat`);
	const example = $derived(
		`curl -X POST https://api.example.com/agent/instances/${instanceId}/chat \\
  -H "Authorization: Bearer <token>" \\
  -H "X-Tenant-ID: <tenant>" \\
  -H "Content-Type: application/json" \\
  -d '{"message": "Hello"}'`
	);

	function copy(text: string) {
		navigator.clipboard.writeText(text);
		toast.success('Copied.');
	}

	function rotateToken() {
		toast.info('Token rotation coming soon.');
	}
</script>

<div class="space-y-4">
	<div class="space-y-1.5">
		<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Endpoint</label>
		<div class="flex items-center gap-2 rounded border bg-[var(--canvas)] px-3 py-2 font-mono text-xs" style="border-color:var(--ds-border)">
			<Badge variant="default" class="text-[10px]">POST</Badge>
			<span class="truncate">{endpoint}</span>
			<Button variant="ghost" size="icon-xs" onclick={() => copy(endpoint)}>
				<Copy />
			</Button>
		</div>
	</div>

	<div class="space-y-1.5">
		<div class="flex items-center justify-between">
			<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">API token</label>
			<Button variant="ghost" size="xs" onclick={rotateToken}>
				<RefreshCw data-icon="inline-start" />
				Rotate
			</Button>
		</div>
		<div class="rounded border bg-[var(--canvas)] px-3 py-2 font-mono text-xs text-muted-foreground" style="border-color:var(--ds-border)">
			Use the user/tenant Bearer token. Per-channel tokens coming soon.
		</div>
	</div>

	<div class="space-y-1.5">
		<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Example</label>
		<div class="flex items-start gap-2">
			<pre class="flex-1 overflow-x-auto rounded border bg-[var(--canvas)] p-3 text-[11px] font-mono leading-relaxed" style="border-color:var(--ds-border)">{example}</pre>
			<Button variant="outline" size="icon-sm" onclick={() => copy(example)}>
				<Copy />
			</Button>
		</div>
	</div>
</div>
