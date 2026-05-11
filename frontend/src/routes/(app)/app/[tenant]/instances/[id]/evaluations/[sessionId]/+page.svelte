<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import MessagesSquare from '@lucide/svelte/icons/messages-square';
	import RunTracePanel from '$lib/components/instance/run-trace-panel.svelte';

	let { data } = $props();

	const sessionId = $derived(page.params.sessionId!);
</script>

<div class="flex h-full flex-col overflow-hidden">
	<header
		class="flex items-center justify-between border-b px-4 py-3"
		style="border-color:var(--ds-border);background:var(--surface)"
	>
		<div class="flex items-center gap-3">
			<button
				type="button"
				onclick={() => goto('./')}
				class="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-[var(--surface-hover)] hover:text-foreground"
			>
				<ArrowLeft class="size-3.5" />
				Sessions
			</button>
			<span class="h-4 w-px bg-[var(--ds-border)]"></span>
			<MessagesSquare class="size-3.5 text-purple-400" />
			<span class="text-xs font-semibold" style="color:var(--text-main)">
				Session #{sessionId.slice(0, 8)}
			</span>
		</div>
	</header>
	<div class="flex-1 overflow-hidden">
		<RunTracePanel instanceId={data.instance.id} {sessionId} />
	</div>
</div>
