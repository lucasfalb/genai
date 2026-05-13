<script lang="ts">
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import Braces from '@lucide/svelte/icons/braces';
	import Wand2 from '@lucide/svelte/icons/wand-2';
	import CircleAlert from '@lucide/svelte/icons/circle-alert';
	import CircleCheck from '@lucide/svelte/icons/circle-check';

	let {
		field,
		value = '',
		label,
		description,
		rows = 7,
		placeholder = '{}',
		required = false,
		error = '',
		onValueChange,
		onError,
		onClear
	}: {
		field: string;
		value?: string;
		label: string;
		description: string;
		rows?: number;
		placeholder?: string;
		required?: boolean;
		error?: string;
		onValueChange: (field: any, value: string) => void;
		onError: (field: any, message: string) => void;
		onClear: (field: any) => void;
	} = $props();

	function lineNumbers(raw: string): string {
		const count = Math.max(raw.split('\n').length, 1);
		return Array.from({ length: count }, (_, index) => index + 1).join('\n');
	}

	function editorRows(raw: string, minRows: number): number {
		return Math.max(raw.split('\n').length, minRows);
	}

	function summary(raw: string): string {
		try {
			const parsed = JSON.parse(raw || '{}');
			if (Array.isArray(parsed)) return `${parsed.length} item${parsed.length === 1 ? '' : 's'}`;
			if (parsed && typeof parsed === 'object') {
				const count = Object.keys(parsed).length;
				return `${count} key${count === 1 ? '' : 's'}`;
			}
			return typeof parsed;
		} catch {
			return 'invalid';
		}
	}

	function format() {
		const raw = value.trim();
		if (!raw) {
			onValueChange(field, field === 'variables_schema' ? '[]' : '{}');
			onClear(field);
			return;
		}
		try {
			onValueChange(field, JSON.stringify(JSON.parse(raw), null, 2));
			onClear(field);
		} catch (formatError) {
			onError(field, formatError instanceof Error ? formatError.message : 'Invalid JSON.');
		}
	}
</script>

<div class="json-card" data-invalid={!!error}>
	<div class="json-card-header">
		<div class="flex min-w-0 items-center gap-2">
			<div class="flex size-7 shrink-0 items-center justify-center rounded-md border bg-background">
				<Braces class="size-3.5 text-muted-foreground" />
			</div>
			<div class="min-w-0">
				<label for={`json-${field}`} class="block truncate text-xs font-medium text-foreground">
					{label}{#if required}<span class="text-red-400"> *</span>{/if}
				</label>
				<p class="truncate text-[10px] text-muted-foreground">{description}</p>
			</div>
		</div>
		<div class="flex shrink-0 items-center gap-2">
			<span
				class="hidden rounded-sm border bg-background px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground sm:inline-flex"
			>
				{summary(value)}
			</span>
			<Tooltip.Root>
				<Tooltip.Trigger
					class="inline-flex size-6 items-center justify-center rounded-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
					aria-label={`Format ${label}`}
					onclick={format}
				>
					<Wand2 class="size-3.5" />
				</Tooltip.Trigger>
				<Tooltip.Content>Format JSON</Tooltip.Content>
			</Tooltip.Root>
		</div>
	</div>
	<div class="json-editor-shell">
		<pre class="json-line-numbers" aria-hidden="true">{lineNumbers(value)}</pre>
		<textarea
			id={`json-${field}`}
			{value}
			oninput={(event) => onValueChange(field, event.currentTarget.value)}
			class="json-editor"
			rows={editorRows(value, rows)}
			{placeholder}
			spellcheck="false"
			wrap="soft"
			aria-invalid={!!error}
		></textarea>
	</div>
	<div class="flex items-start justify-between gap-3 border-t bg-muted/20 px-3 py-2">
		{#if error}
			<p class="flex shrink-0 items-center gap-1 text-[10px] text-red-400">
				<CircleAlert class="size-3" />
				{error}
			</p>
		{:else}
			<p class="flex shrink-0 items-center gap-1 text-[10px] text-emerald-500">
				<CircleCheck class="size-3" />
				Valid JSON
			</p>
		{/if}
	</div>
</div>

<style>
	.json-card {
		overflow: hidden;
		border: 1px solid color-mix(in oklab, var(--border) 88%, var(--foreground) 12%);
		background: color-mix(in oklab, var(--background) 92%, black 8%);
		border-radius: 8px;
	}

	.json-card[data-invalid='true'] {
		border-color: color-mix(in oklab, var(--destructive) 55%, var(--border));
		box-shadow: 0 0 0 1px color-mix(in oklab, var(--destructive) 18%, transparent);
	}

	.json-card-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		border-bottom: 1px solid var(--border);
		background: linear-gradient(
			180deg,
			color-mix(in oklab, var(--muted) 60%, transparent),
			color-mix(in oklab, var(--background) 86%, black 14%)
		);
		padding: 0.625rem 0.75rem;
	}

	.json-editor-shell {
		display: grid;
		grid-template-columns: 2.75rem minmax(0, 1fr);
		max-height: 34rem;
		overflow: auto;
		background:
			linear-gradient(
				90deg,
				color-mix(in oklab, var(--muted) 48%, transparent) 0 2.75rem,
				transparent 2.75rem
			),
			repeating-linear-gradient(
				180deg,
				color-mix(in oklab, var(--background) 88%, black 12%) 0,
				color-mix(in oklab, var(--background) 88%, black 12%) 1.5rem,
				color-mix(in oklab, var(--muted) 18%, transparent) 1.5rem,
				color-mix(in oklab, var(--muted) 18%, transparent) 3rem
			);
	}

	.json-line-numbers {
		margin: 0;
		user-select: none;
		border-right: 1px solid var(--border);
		padding: 0.75rem 0.625rem;
		text-align: right;
		font-family:
			ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
		font-size: 0.6875rem;
		line-height: 1.5;
		color: color-mix(in oklab, var(--muted-foreground) 82%, transparent);
	}

	.json-editor {
		min-height: 0;
		width: 100%;
		resize: none;
		border: 0;
		background: transparent;
		padding: 0.75rem;
		font-family:
			ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
		font-size: 0.75rem;
		line-height: 1.5;
		color: color-mix(in oklab, var(--foreground) 92%, #7dd3fc 8%);
		caret-color: color-mix(in oklab, var(--ring) 65%, var(--foreground));
		tab-size: 2;
		outline: none;
		overflow: hidden;
		white-space: pre-wrap;
		overflow-wrap: anywhere;
		text-shadow: 0 0 0.01px currentColor;
	}

	.json-editor::selection {
		background: color-mix(in oklab, var(--ring) 42%, transparent);
		color: var(--foreground);
	}

	.json-editor::placeholder {
		color: color-mix(in oklab, var(--muted-foreground) 62%, transparent);
	}

	.json-editor:focus {
		background: color-mix(in oklab, var(--ring) 5%, transparent);
		box-shadow: inset 0 0 0 1px color-mix(in oklab, var(--ring) 82%, transparent);
	}
</style>
