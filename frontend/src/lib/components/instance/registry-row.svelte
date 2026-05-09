<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import JsonConfigPanel from '$lib/components/JsonConfigPanel.svelte';

	let {
		slug,
		id,
		is_enabled,
		config,
		busy,
		expanded,
		onToggle,
		onExpandToggle,
		onConfigSave
	}: {
		slug: string;
		id: string;
		is_enabled: boolean;
		config: Record<string, unknown>;
		busy: boolean;
		expanded: boolean;
		onToggle: () => void;
		onExpandToggle: () => void;
		onConfigSave: (config: Record<string, unknown>) => void | Promise<void>;
	} = $props();

	function parseJsonConfig(json: string): Record<string, unknown> {
		return JSON.parse(json || '{}') as Record<string, unknown>;
	}
</script>

<div class="rounded-lg p-4" style="background:var(--surface-hover);border:1px solid var(--ds-border)">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div class="min-w-0">
			<p class="font-mono text-sm font-semibold" style="color:var(--text-main)">{slug}</p>
			<p class="mt-0.5 text-xs text-muted-foreground/70">{id}</p>
		</div>
		<div class="flex items-center gap-2">
			<Badge variant={is_enabled ? 'default' : 'outline'}>
				{is_enabled ? 'Enabled' : 'Disabled'}
			</Badge>
			<Button
				variant={is_enabled ? 'destructive' : 'outline'}
				size="sm"
				disabled={busy}
				onclick={onToggle}
			>
				{#if busy}<Spinner data-icon="inline-start" />{/if}
				{busy ? 'Saving...' : is_enabled ? 'Disable' : 'Enable'}
			</Button>
			<Button variant="ghost" size="sm" onclick={onExpandToggle}>
				Config
			</Button>
		</div>
	</div>
	{#if expanded}
		<div class="mt-4">
			<JsonConfigPanel
				value={JSON.stringify(config ?? {}, null, 2)}
				onSave={async (json) => onConfigSave(parseJsonConfig(json))}
			/>
		</div>
	{/if}
</div>
