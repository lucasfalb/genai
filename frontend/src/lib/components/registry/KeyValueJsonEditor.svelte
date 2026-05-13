<script lang="ts">
	import { Input } from '$lib/components/ui/input/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import JsonEditor from './JsonEditor.svelte';
	import Key from '@lucide/svelte/icons/key';
	import Plus from '@lucide/svelte/icons/plus';
	import X from '@lucide/svelte/icons/x';

	type EditorView = 'inputs' | 'json';
	type Row = { key: string; value: string };

	let {
		field,
		value = '{}',
		label,
		description,
		keyPlaceholder,
		valuePlaceholder,
		resetKey,
		error = '',
		onValueChange,
		onError,
		onClear
	}: {
		field: string;
		value?: string;
		label: string;
		description: string;
		keyPlaceholder: string;
		valuePlaceholder: string;
		resetKey: string;
		error?: string;
		onValueChange: (field: any, value: string) => void;
		onError: (field: any, message: string) => void;
		onClear: (field: any) => void;
	} = $props();

	let view = $state<EditorView>('inputs');
	let rows = $state<Row[]>([{ key: '', value: '' }]);
	let lastResetKey = $state('');

	$effect(() => {
		if (lastResetKey === resetKey) return;
		lastResetKey = resetKey;
		view = 'inputs';
		rows = parseRows(value || '{}');
	});

	function parseRows(raw: string): Row[] {
		try {
			const parsed = JSON.parse(raw || '{}');
			if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return [{ key: '', value: '' }];
			const parsedRows = Object.entries(parsed).map(([entryKey, entryValue]) => ({
				key: entryKey,
				value: typeof entryValue === 'string' ? entryValue : JSON.stringify(entryValue)
			}));
			return parsedRows.length ? parsedRows : [{ key: '', value: '' }];
		} catch {
			return [{ key: '', value: '' }];
		}
	}

	function writeRows(nextRows: Row[]) {
		const payload = nextRows.reduce<Record<string, string>>((acc, row) => {
			const key = row.key.trim();
			if (key) acc[key] = row.value;
			return acc;
		}, {});
		rows = nextRows;
		onValueChange(field, JSON.stringify(payload, null, 2));
	}

	function setView(nextView: EditorView) {
		if (nextView === 'json') writeRows(rows);
		else rows = parseRows(value || '{}');
		view = nextView;
	}

	function updateRow(index: number, column: keyof Row, nextValue: string) {
		const nextRows = rows.slice();
		nextRows[index] = { ...nextRows[index], [column]: nextValue };
		writeRows(nextRows);
	}

	function addRow() {
		rows = [...rows, { key: '', value: '' }];
	}

	function removeRow(index: number) {
		const nextRows = rows.filter((_, rowIndex) => rowIndex !== index);
		writeRows(nextRows.length ? nextRows : [{ key: '', value: '' }]);
	}
</script>

<div class="rounded-lg border">
	<div class="flex items-center justify-between gap-3 border-b bg-muted/40 px-3 py-2">
		<div class="flex min-w-0 items-center gap-2">
			<div class="flex size-7 shrink-0 items-center justify-center rounded-md border bg-background">
				<Key class="size-3.5 text-muted-foreground" />
			</div>
			<div class="min-w-0">
				<p class="truncate text-xs font-medium text-foreground">{label}</p>
				<p class="truncate text-[10px] text-muted-foreground">{description}</p>
			</div>
		</div>
		<div class="flex items-center gap-1 rounded-sm border bg-muted/20 p-0.5">
			<button
				type="button"
				class="rounded-xs px-2 py-1 text-[10px] font-medium transition-colors {view === 'inputs' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}"
				onclick={() => setView('inputs')}
			>
				Inputs
			</button>
			<button
				type="button"
				class="rounded-xs px-2 py-1 text-[10px] font-medium transition-colors {view === 'json' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}"
				onclick={() => setView('json')}
			>
				JSON
			</button>
		</div>
	</div>

	{#if view === 'json'}
		<div class="p-3">
			<JsonEditor
				{field}
				{value}
				{label}
				{description}
				rows={field === 'body_template' ? 7 : 5}
				placeholder={field === 'body_template'
					? '{\n  "query": "{query}",\n  "limit": "10"\n}'
					: '{\n  "Authorization": "Bearer {token}"\n}'}
				{error}
				{onValueChange}
				{onError}
				{onClear}
			/>
		</div>
	{:else}
		<div class="flex flex-col gap-2 p-3">
			<div class="grid grid-cols-[minmax(0,0.9fr)_minmax(0,1.4fr)_2rem] gap-2 text-[10px] font-medium text-muted-foreground">
				<span>Key</span>
				<span>Value</span>
				<span class="sr-only">Actions</span>
			</div>
			{#each rows as row, index}
				<div class="grid grid-cols-[minmax(0,0.9fr)_minmax(0,1.4fr)_2rem] gap-2">
					<Input
						value={row.key}
						placeholder={keyPlaceholder}
						class="font-mono text-xs"
						oninput={(event) => updateRow(index, 'key', event.currentTarget.value)}
					/>
					<Input
						value={row.value}
						placeholder={valuePlaceholder}
						class="font-mono text-xs"
						oninput={(event) => updateRow(index, 'value', event.currentTarget.value)}
					/>
					<Button
						type="button"
						variant="ghost"
						size="icon-sm"
						aria-label={`Remove ${label} row`}
						onclick={() => removeRow(index)}
					>
						<X />
					</Button>
				</div>
			{/each}
			<div>
				<Button type="button" variant="outline" size="sm" onclick={addRow}>
					<Plus data-icon="inline-start" />
					Add row
				</Button>
			</div>
		</div>
	{/if}
</div>
