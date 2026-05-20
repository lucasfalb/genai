<script lang="ts">
	import { page } from '$app/stores';
	import X from '@lucide/svelte/icons/x';
	import Bot from '@lucide/svelte/icons/bot';
	import Clock3 from '@lucide/svelte/icons/clock-3';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import type { RunTraceListItem } from '$lib/api/types';
	import { renderFormattedMessage } from '$lib/utils/rich-message';

	type PreviewProps = {
		run: RunTraceListItem;
		instanceName: string;
		closeToast?: () => void;
	};

	let { run, instanceName, closeToast }: PreviewProps = $props();

	function fmtInt(value: number | null | undefined) {
		return new Intl.NumberFormat('en-US').format(value ?? 0);
	}

	function fmtDuration(ms: number) {
		if (ms < 1000) return `${ms}ms`;
		return `${(ms / 1000).toFixed(1)}s`;
	}

	function fmtDate(value: string) {
		return new Intl.DateTimeFormat('pt-BR', {
			day: '2-digit',
			month: '2-digit',
			hour: '2-digit',
			minute: '2-digit',
			second: '2-digit'
		}).format(new Date(value));
	}

	function fmtStatus(run: RunTraceListItem) {
		if (run.final_response_preview) return { label: 'Completed', class: 'text-emerald-400' };
		if (run.completed_at && !run.final_response_preview) return { label: 'Failed', class: 'text-red-400' };
		return { label: 'Running', class: 'text-amber-400' };
	}

	const status = $derived(fmtStatus(run));
	const debugUrl = $derived(
		`/${$page.params.tenant}/instances/${run.instance_id}/debug`
	);
</script>

<div class="w-[360px] space-y-3">
	<div class="flex items-center justify-between gap-2">
		<div class="flex items-center gap-2 min-w-0">
			<Bot class="size-4 shrink-0 text-blue-400" />
			<span class="truncate text-sm font-medium">{instanceName}</span>
		</div>
		<button
			type="button"
			onclick={closeToast}
			class="flex size-5 shrink-0 items-center justify-center rounded hover:bg-muted"
		>
			<X class="size-3.5" />
		</button>
	</div>

	<div class="flex items-center gap-3 text-xs text-muted-foreground">
		<span class="font-mono text-[11px]">{run.run_id.slice(0, 12)}</span>
		<span class="flex items-center gap-1">
			<Clock3 class="size-3" />
			{fmtDuration(run.duration_ms)}
		</span>
		<span class="{status.class} flex items-center gap-1 text-[11px] font-medium">
			{status.label}
		</span>
	</div>

	<div class="flex flex-wrap gap-1.5">
		<span class="rounded bg-blue-500/10 px-2 py-0.5 font-mono text-[11px] text-blue-400">
			P {fmtInt(run.prompt_tokens)}
		</span>
		<span class="rounded bg-emerald-500/10 px-2 py-0.5 font-mono text-[11px] text-emerald-400">
			C {fmtInt(run.completion_tokens)}
		</span>
		<span class="rounded bg-amber-500/10 px-2 py-0.5 font-mono text-[11px] text-amber-400">
			E {fmtInt(run.embedding_tokens)}
		</span>
		<span class="rounded bg-purple-500/10 px-2 py-0.5 font-mono text-[11px] text-purple-400">
			T {fmtInt((run.total_tokens ?? 0) + (run.embedding_tokens ?? 0))}
		</span>
	</div>

	<div class="space-y-1 text-xs">
		{#if run.user_message}
			<div class="rich-trace-preview line-clamp-2 rounded bg-muted/50 p-2 leading-relaxed text-muted-foreground">
				{@html renderFormattedMessage(run.user_message)}
			</div>
		{/if}
		{#if run.final_response_preview}
			<div class="rich-trace-preview line-clamp-3 rounded bg-muted/30 p-2 leading-relaxed text-muted-foreground">
				{@html renderFormattedMessage(run.final_response_preview)}
			</div>
		{/if}
	</div>

	<div class="flex items-center justify-between gap-2 border-t pt-2 text-[11px]">
		<span class="text-muted-foreground">{fmtDate(run.started_at)}</span>
		<a
			href={debugUrl}
			class="inline-flex items-center gap-1 font-medium text-blue-400 hover:text-blue-300"
		>
			<Sparkles class="size-3" />
			<span>Debug</span>
			<ExternalLink class="size-3" />
		</a>
	</div>
</div>

<style>
	.rich-trace-preview {
		white-space: normal;
	}
	.rich-trace-preview :global(p) {
		margin: 0 0 0.5em;
	}
	.rich-trace-preview :global(p:last-child),
	.rich-trace-preview :global(ul:last-child) {
		margin-bottom: 0;
	}
	.rich-trace-preview :global(ul) {
		margin: 0.25em 0 0.55em;
		padding-left: 1.1em;
	}
	.rich-trace-preview :global(li) {
		margin: 0.15em 0;
	}
	.rich-trace-preview :global(strong) {
		font-weight: 750;
	}
	.rich-trace-preview :global(code) {
		border-radius: 5px;
		background: rgba(148, 163, 184, 0.14);
		padding: 0.05em 0.28em;
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 0.9em;
	}
</style>
