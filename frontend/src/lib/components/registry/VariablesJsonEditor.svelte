<script lang="ts">
	import { Input } from '$lib/components/ui/input/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import JsonEditor from './JsonEditor.svelte';
	import Variable from '@lucide/svelte/icons/variable';
	import Plus from '@lucide/svelte/icons/plus';
	import X from '@lucide/svelte/icons/x';

	type EditorView = 'inputs' | 'json';
	type VariableRow = {
		name: string;
		label: string;
		type: string;
		required: boolean;
		secret: boolean;
		description: string;
		default: string;
	};

	let {
		value = '[]',
		resetKey,
		error = '',
		onValueChange,
		onError,
		onClear
	}: {
		value?: string;
		resetKey: string;
		error?: string;
		onValueChange: (field: any, value: string) => void;
		onError: (field: any, message: string) => void;
		onClear: (field: any) => void;
	} = $props();

	let view = $state<EditorView>('inputs');
	let rows = $state<VariableRow[]>([]);
	let lastResetKey = $state('');

	$effect(() => {
		if (lastResetKey === resetKey) return;
		lastResetKey = resetKey;
		view = 'inputs';
		rows = parseRows(value || '[]');
	});

	function parseRows(raw: string): VariableRow[] {
		try {
			const parsed = JSON.parse(raw || '[]');
			if (!Array.isArray(parsed)) return [];
			return parsed.map((item) => ({
				name: String(item?.name ?? ''),
				label: String(item?.label ?? ''),
				type: String(item?.type ?? 'string'),
				required: Boolean(item?.required),
				secret: Boolean(item?.secret),
				description: String(item?.description ?? ''),
				default: item?.default === undefined ? '' : String(item.default)
			}));
		} catch {
			return [];
		}
	}

	function writeRows(nextRows: VariableRow[]) {
		const payload = nextRows
			.filter((row) => row.name.trim())
			.map((row) => ({
				name: row.name.trim(),
				label: row.label.trim() || row.name.trim(),
				type: row.type || 'string',
				required: row.required,
				secret: row.secret,
				...(row.description.trim() ? { description: row.description.trim() } : {}),
				...(row.default.trim() ? { default: row.default } : {})
			}));
		rows = nextRows;
		onValueChange('variables_schema', JSON.stringify(payload, null, 2));
	}

	function setView(nextView: EditorView) {
		if (nextView === 'json') writeRows(rows);
		else rows = parseRows(value || '[]');
		view = nextView;
	}

	function updateRow(index: number, column: keyof VariableRow, nextValue: string | boolean) {
		const nextRows = rows.slice();
		nextRows[index] = { ...nextRows[index], [column]: nextValue };
		writeRows(nextRows);
	}

	function addRow() {
		writeRows([...rows, {
			name: '',
			label: '',
			type: 'string',
			required: false,
			secret: false,
			description: '',
			default: ''
		}]);
	}

	function removeRow(index: number) {
		writeRows(rows.filter((_, rowIndex) => rowIndex !== index));
	}
</script>

<div class="rounded-lg border">
	<div class="flex items-center justify-between gap-3 border-b bg-muted/40 px-3 py-2">
		<div class="flex min-w-0 items-center gap-2">
			<div class="flex size-7 shrink-0 items-center justify-center rounded-md border bg-background">
				<Variable class="size-3.5 text-muted-foreground" />
			</div>
			<div class="min-w-0">
				<p class="truncate text-xs font-medium text-foreground">Variables</p>
				<p class="truncate text-[10px] text-muted-foreground">Values users configure when enabling this tool on an instance.</p>
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
				field="variables_schema"
				{value}
				label="Variables schema"
				description="JSON array of values users configure when enabling this tool."
				rows={8}
				placeholder={'[\n  {\n    "name": "token",\n    "label": "API Token",\n    "type": "string",\n    "secret": true,\n    "required": true\n  }\n]'}
				{error}
				{onValueChange}
				{onError}
				{onClear}
			/>
		</div>
	{:else}
		<div class="flex flex-col gap-3 p-3">
			{#each rows as variable, index}
				<div class="rounded-md border bg-muted/10 p-3">
					<div class="grid grid-cols-[minmax(0,1fr)_2rem] gap-2">
						<div class="flex flex-col gap-1">
							<label class="text-[10px] font-medium text-muted-foreground" for={`variable-key-${index}`}>
								Key
							</label>
							<Input
								id={`variable-key-${index}`}
								value={variable.name}
								placeholder="api_key"
								class="font-mono text-xs"
								oninput={(event) => updateRow(index, 'name', event.currentTarget.value)}
							/>
						</div>
						<Button
							type="button"
							variant="ghost"
							size="icon-sm"
							aria-label="Remove variable"
							onclick={() => removeRow(index)}
							class="self-end"
						>
							<X />
						</Button>
					</div>
					<div class="mt-2 grid grid-cols-2 gap-2">
						<div class="flex flex-col gap-1">
							<label class="text-[10px] font-medium text-muted-foreground" for={`variable-label-${index}`}>
								Label
							</label>
							<Input
								id={`variable-label-${index}`}
								value={variable.label}
								placeholder="Optional display name"
								class="text-xs"
								oninput={(event) => updateRow(index, 'label', event.currentTarget.value)}
							/>
						</div>
						<div class="flex flex-col gap-1">
							<label class="text-[10px] font-medium text-muted-foreground" for={`variable-type-${index}`}>
								Type
							</label>
							<Select.Root
								type="single"
								value={variable.type}
								onValueChange={(value) => updateRow(index, 'type', value)}
							>
								<Select.Trigger id={`variable-type-${index}`} class="h-9 w-full bg-background font-mono text-xs">
									{variable.type || 'string'}
								</Select.Trigger>
								<Select.Content>
									{#each ['string', 'number', 'boolean', 'object'] as typeOption}
										<Select.Item value={typeOption} label={typeOption}>{typeOption}</Select.Item>
									{/each}
								</Select.Content>
							</Select.Root>
						</div>
					</div>
					<div class="mt-2 grid grid-cols-2 gap-2">
						<Input
							value={variable.description}
							placeholder="Description"
							class="text-xs"
							oninput={(event) => updateRow(index, 'description', event.currentTarget.value)}
						/>
						<Input
							value={variable.default}
							placeholder="Default value"
							class="font-mono text-xs"
							oninput={(event) => updateRow(index, 'default', event.currentTarget.value)}
						/>
					</div>
					<div class="mt-2 flex items-center gap-4 text-xs">
						<label class="flex items-center gap-2 text-muted-foreground">
							<input
								type="checkbox"
								checked={variable.required}
								onchange={(event) => updateRow(index, 'required', event.currentTarget.checked)}
							/>
							Required
						</label>
						<label class="flex items-center gap-2 text-muted-foreground">
							<input
								type="checkbox"
								checked={variable.secret}
								onchange={(event) => updateRow(index, 'secret', event.currentTarget.checked)}
							/>
							Secret
						</label>
					</div>
				</div>
			{/each}

			{#if rows.length === 0}
				<div class="rounded-md border border-dashed px-3 py-4 text-center text-xs text-muted-foreground">
					No variables yet.
				</div>
			{/if}

			<div>
				<Button type="button" variant="outline" size="sm" onclick={addRow}>
					<Plus data-icon="inline-start" />
					Add variable
				</Button>
			</div>
		</div>
	{/if}
</div>
