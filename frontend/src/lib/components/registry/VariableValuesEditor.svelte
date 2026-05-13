<script lang="ts">
	import { Input } from '$lib/components/ui/input/index.js';
	import JsonEditor from './JsonEditor.svelte';
	import Variable from '@lucide/svelte/icons/variable';
	import type { ToolVariableSpec } from '$lib/api/types';

	type EditorView = 'inputs' | 'json';

	let {
		specs = [],
		values = {},
		resetKey,
		onValuesChange
	}: {
		specs?: ToolVariableSpec[];
		values?: Record<string, string>;
		resetKey: string;
		onValuesChange: (values: Record<string, string>) => void;
	} = $props();

	let view = $state<EditorView>('inputs');
	let rawJson = $state('{}');
	let jsonError = $state('');
	let lastResetKey = $state('');

	$effect(() => {
		if (lastResetKey === resetKey) return;
		lastResetKey = resetKey;
		view = 'inputs';
		rawJson = JSON.stringify(values, null, 2);
		jsonError = '';
	});

	function updateValue(name: string, value: string) {
		onValuesChange({ ...values, [name]: value });
	}

	function setView(nextView: EditorView) {
		if (nextView === 'json') rawJson = JSON.stringify(values, null, 2);
		if (nextView === 'inputs') applyJson();
		view = nextView;
	}

	function setJson(_field: string, value: string) {
		rawJson = value;
		try {
			const parsed = JSON.parse(value || '{}');
			if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
				const nextValues = Object.fromEntries(
					Object.entries(parsed).map(([key, entryValue]) => [key, entryValue == null ? '' : String(entryValue)])
				);
				onValuesChange(nextValues);
				jsonError = '';
			} else {
				jsonError = 'Variables JSON must be an object.';
			}
		} catch {
			jsonError = 'Variables JSON is invalid.';
		}
	}

	function setJsonError(_field: string, message: string) {
		jsonError = message;
	}

	function clearJsonError() {
		jsonError = '';
	}

	function applyJson() {
		if (!rawJson.trim()) {
			onValuesChange({});
			jsonError = '';
			return;
		}
		try {
			const parsed = JSON.parse(rawJson);
			if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
				onValuesChange(Object.fromEntries(
					Object.entries(parsed).map(([key, entryValue]) => [key, entryValue == null ? '' : String(entryValue)])
				));
				jsonError = '';
			}
		} catch {
			jsonError = 'Variables JSON is invalid.';
		}
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
				<p class="truncate text-[10px] text-muted-foreground">Values stored on this instance and available as placeholders.</p>
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
				field="variables"
				value={rawJson}
				label="Variables"
				description="JSON object with the values this instance provides to placeholders."
				rows={7}
				error={jsonError}
				onValueChange={setJson}
				onError={setJsonError}
				onClear={clearJsonError}
			/>
		</div>
	{:else}
		<div class="flex flex-col gap-3 p-3">
			{#if specs.length === 0}
				<div class="rounded-md border border-dashed px-3 py-4 text-center text-xs text-muted-foreground">
					No variables defined by this tool.
				</div>
			{:else}
				{#each specs as spec (spec.name)}
					<div class="flex flex-col gap-1.5">
						<label class="text-xs font-medium text-foreground/80" for={`tool-variable-${spec.name}`}>
							{spec.label ?? spec.name}
							{#if spec.required}<span class="text-red-400">*</span>{/if}
						</label>
						{#if spec.description}
							<p class="text-[11px] text-muted-foreground/70">{spec.description}</p>
						{/if}
						<Input
							id={`tool-variable-${spec.name}`}
							type={spec.secret ? 'password' : 'text'}
							value={values[spec.name] ?? ''}
							oninput={(event) => updateValue(spec.name, event.currentTarget.value)}
							class="font-mono text-xs"
						/>
					</div>
				{/each}
			{/if}
		</div>
	{/if}
</div>
