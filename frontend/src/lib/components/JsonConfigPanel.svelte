<script lang="ts">
	let {
		value,
		onSave
	}: {
		value: string;
		onSave: (json: string) => Promise<void>;
	} = $props();

	let text = $state('');
	let error = $state('');
	let saving = $state(false);

	$effect(() => {
		text = value;
		error = '';
	});

	function validate(): boolean {
		try {
			JSON.parse(text || '{}');
			error = '';
			return true;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Invalid JSON.';
			return false;
		}
	}

	async function save() {
		if (!validate()) return;
		saving = true;
		try {
			await onSave(text || '{}');
		} finally {
			saving = false;
		}
	}
</script>

<div class="space-y-3 rounded-lg p-4" style="background:var(--surface-hover);border:1px solid var(--ds-border)">
	<textarea
		value={text}
		oninput={(event) => {
			text = event.currentTarget.value;
			if (error) validate();
		}}
		onblur={validate}
		rows="8"
		class="auth-input w-full resize-y rounded-lg px-3 py-2 font-mono text-xs leading-relaxed"
		spellcheck="false"
	></textarea>
	{#if error}
		<p class="text-xs text-red-400">{error}</p>
	{/if}
	<div class="flex justify-end">
		<button
			onclick={save}
			disabled={saving || !!error}
			class="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-blue-500 disabled:opacity-60"
		>
			{saving ? 'Saving...' : 'Save JSON'}
		</button>
	</div>
</div>
