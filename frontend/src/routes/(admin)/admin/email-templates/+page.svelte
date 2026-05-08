<script lang="ts">
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { superadminApi } from '$lib/api/superadmin';
	import { getErrorMessage } from '$lib/api/client';
	import type { EmailTemplateResponse } from '$lib/api/types';
	import { toast } from 'svelte-sonner';
	import Mail from '@lucide/svelte/icons/mail';
	import X from '@lucide/svelte/icons/x';

	let { data } = $props();

	const FORMATS = ['html', 'text'];

	let templates = $state<EmailTemplateResponse[]>(data.templates);
	let editing = $state<EmailTemplateResponse | null>(null);
	let busy = $state(false);

	let editName = $state('');
	let editDescription = $state('');
	let editSubject = $state('');
	let editBody = $state('');
	let editFormat = $state('html');
	let editIsActive = $state(true);
	let editVariablesSchema = $state('{}');

	function startEdit(t: EmailTemplateResponse) {
		editing = t;
		editName = t.name;
		editDescription = t.description ?? '';
		editSubject = t.subject_template;
		editBody = t.body_template;
		editFormat = t.body_format ?? 'html';
		editIsActive = t.is_active;
		editVariablesSchema = JSON.stringify(t.variables_schema ?? {}, null, 2);
	}

	const variablesList = $derived(
		editing ? Object.keys(editing.variables_schema ?? {}) : []
	);

	async function save() {
		if (!editing) return;
		let variablesSchema: Record<string, unknown> = {};
		try {
			variablesSchema = JSON.parse(editVariablesSchema || '{}');
		} catch {
			toast.error('Variables schema JSON is invalid.');
			return;
		}
		busy = true;
		try {
			const updated = await superadminApi.saveTemplate(editing.slug, {
				slug: editing.slug,
				name: editName.trim(),
				description: editDescription.trim(),
				subject_template: editSubject,
				body_template: editBody,
				body_format: editFormat,
				is_active: editIsActive,
				variables_schema: variablesSchema
			});
			templates = templates.map((t) => (t.slug === updated.slug ? updated : t));
			editing = updated;
			toast.success('Template saved.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Save failed.'));
		} finally {
			busy = false;
		}
	}
</script>

<div class="space-y-6 p-6">
	<div class="flex items-center gap-3">
		<div class="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
			<Mail class="h-4 w-4" />
		</div>
		<div>
			<h1 class="font-display text-lg font-semibold" style="color:var(--text-main)">Email Templates</h1>
			<p class="text-xs text-muted-foreground">{templates.length} templates</p>
		</div>
	</div>

	<div class="rounded-xl" style="background:var(--surface);border:1px solid var(--ds-border)">
		{#if templates.length === 0}
			<p class="py-12 text-center text-sm text-muted-foreground">No templates found.</p>
		{:else}
			<div class="overflow-x-auto">
				<table class="w-full text-left text-sm">
					<thead class="border-b text-xs uppercase tracking-widest text-muted-foreground" style="border-color:var(--ds-border)">
						<tr>
							<th class="px-4 py-3 font-semibold">Slug</th>
							<th class="px-4 py-3 font-semibold">Name</th>
							<th class="px-4 py-3 font-semibold">Format</th>
							<th class="px-4 py-3 font-semibold">Active</th>
						</tr>
					</thead>
					<tbody>
						{#each templates as t (t.slug)}
							<tr
								onclick={() => startEdit(t)}
								class="cursor-pointer border-b last:border-b-0 transition-colors hover:bg-white/2 {editing?.slug === t.slug ? 'bg-blue-500/5' : ''}"
								style="border-color:var(--ds-border)"
							>
								<td class="px-4 py-3 font-mono text-xs" style="color:var(--text-main)">{t.slug}</td>
								<td class="px-4 py-3 text-sm" style="color:var(--text-main)">{t.name}</td>
								<td class="px-4 py-3 text-xs text-muted-foreground">{t.body_format ?? 'html'}</td>
								<td class="px-4 py-3">
									<span class="rounded-full px-2 py-1 text-[10px] font-semibold {t.is_active ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-500/10 text-muted-foreground'}">
										{t.is_active ? 'Active' : 'Inactive'}
									</span>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</div>

	{#if editing}
		<div class="rounded-xl p-5 space-y-4" style="background:var(--surface);border:1px solid var(--ds-border)">
			<div class="flex items-center justify-between">
				<div>
					<h2 class="text-sm font-semibold" style="color:var(--text-main)">Edit {editing.slug}</h2>
					{#if variablesList.length > 0}
						<p class="mt-1 text-xs text-muted-foreground">
							Variables: {variablesList.map((v) => `{{${v}}}`).join(', ')}
						</p>
					{/if}
				</div>
				<button onclick={() => (editing = null)} class="rounded-lg p-1 text-muted-foreground hover:text-foreground">
					<X class="h-4 w-4" />
				</button>
			</div>

			<div class="grid grid-cols-2 gap-4">
				<div class="space-y-1">
					<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Name</label>
					<input bind:value={editName} class="auth-input w-full rounded-lg px-3 py-2 text-sm" />
				</div>
				<div class="space-y-1">
					<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Format</label>
					<select bind:value={editFormat} class="auth-input w-full rounded-lg px-3 py-2 text-sm">
						{#each FORMATS as f (f)}<option value={f}>{f}</option>{/each}
					</select>
				</div>
				<div class="col-span-2 space-y-1">
					<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Description</label>
					<input bind:value={editDescription} class="auth-input w-full rounded-lg px-3 py-2 text-sm" />
				</div>
			</div>

			<div class="space-y-1">
				<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Subject Template</label>
				<input bind:value={editSubject} class="auth-input w-full rounded-lg px-3 py-2 font-mono text-sm" />
			</div>

			<div class="space-y-1">
				<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Body Template</label>
				<textarea bind:value={editBody} rows={10} class="auth-input w-full rounded-lg px-3 py-2 font-mono text-xs" style="resize:vertical"></textarea>
			</div>

			<div class="space-y-1">
				<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Variables Schema JSON</label>
				<textarea bind:value={editVariablesSchema} rows={4} class="auth-input w-full rounded-lg px-3 py-2 font-mono text-xs" style="resize:vertical"></textarea>
			</div>

			<div class="flex items-center justify-between rounded-lg px-3.5 py-3" style="background:var(--surface-hover);border:1px solid var(--ds-border)">
				<p class="text-sm" style="color:var(--text-main)">Active</p>
				<Switch bind:checked={editIsActive} />
			</div>

			<div class="flex justify-end">
				<button
					onclick={save}
					disabled={busy}
					class="rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-40"
					style="background:var(--text-main);color:var(--canvas)"
				>
					{busy ? 'Saving...' : 'Save Template'}
				</button>
			</div>
		</div>
	{/if}
</div>
