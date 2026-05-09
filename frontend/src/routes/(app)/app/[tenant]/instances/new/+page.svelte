<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Bot from '@lucide/svelte/icons/bot';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import { instancesApi } from '$lib/api/instances';
	import { ApiError } from '$lib/api/client';
	import { tenantBaseFromPath } from '$lib/routes/tenant';
	import { getAgentUiSettings, type AgentTemplateOption } from '$lib/settings/agent-ui';

	let { data } = $props();
	const agentUi = getAgentUiSettings(data.publicSettings);

	let name = $state('');
	let description = $state('');
	let core_prompt = $state('');
	let model = $state(agentUi.default_model);
	let temperature = $state(0.7);
	let loading = $state(false);
	let error = $state('');
	const appBase = $derived(tenantBaseFromPath(page.url.pathname));

	function applyTemplate(template: AgentTemplateOption) {
		name = template.name;
		description = template.description;
		core_prompt = template.core_prompt;
	}

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!name.trim()) { error = 'Name is required.'; return; }
		if (!core_prompt.trim()) { error = 'Core prompt is required.'; return; }
		error = '';
		loading = true;
		try {
			const inst = await instancesApi.create({
				name: name.trim(),
				description: description.trim() || undefined,
				core_prompt: core_prompt.trim(),
				model,
				temperature
			});
			await goto(`${appBase}/instances/${inst.id}`);
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Failed to create instance.';
		} finally {
			loading = false;
		}
	}
</script>

<div class="mb-6 flex items-center gap-3 px-6 pt-6">
	<a href="{appBase}/instances" class="rounded-lg p-1.5 transition-colors hover:bg-white/5">
		<ArrowLeft class="h-4 w-4 text-muted-foreground" />
	</a>
	<div>
		<h1 class="font-display text-xl font-semibold" style="color:var(--text-main)">New Agent</h1>
		<p class="mt-0.5 text-sm text-muted-foreground">Configure a new tenant agent</p>
	</div>
</div>

<form onsubmit={handleSubmit} class="mx-auto grid max-w-6xl gap-5 px-6 pb-8 lg:grid-cols-[320px_1fr]">
	{#if error}
		<div
			class="rounded-xl px-4 py-3 text-sm text-red-400 lg:col-span-2"
			style="background:color-mix(in srgb,red 8%,transparent);border:1px solid color-mix(in srgb,red 18%,transparent)"
		>{error}</div>
	{/if}

	<section class="rounded-xl p-5" style="background:var(--surface);border:1px solid var(--ds-border)">
		<div class="mb-4 flex items-center gap-2">
			<Sparkles class="size-4 text-blue-400" />
			<h2 class="font-display text-sm font-semibold" style="color:var(--text-main)">Start from a template</h2>
		</div>
		<div class="space-y-2">
			{#each agentUi.templates as template (template.name)}
				<button type="button" onclick={() => applyTemplate(template)} class="w-full rounded-lg border p-3 text-left transition-colors hover:bg-white/[0.03]" style="border-color:var(--ds-border)">
					<p class="text-sm font-semibold" style="color:var(--text-main)">{template.name}</p>
					<p class="mt-1 line-clamp-2 text-xs text-muted-foreground">{template.description}</p>
				</button>
			{/each}
		</div>
	</section>

	<div class="space-y-5">
	<div class="rounded-xl p-6 space-y-5" style="background:var(--surface);border:1px solid var(--ds-border)">
		<h2 class="font-display text-sm font-semibold" style="color:var(--text-main)">Details</h2>

		<div class="space-y-1.5">
			<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Name *</label>
			<input
				type="text"
				bind:value={name}
				placeholder="e.g. Support Agent"
				class="auth-input w-full rounded-lg px-3.5 py-2.5 text-sm"
			/>
		</div>

		<div class="space-y-1.5">
			<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Description</label>
			<input
				type="text"
				bind:value={description}
				placeholder="Optional short description"
				class="auth-input w-full rounded-lg px-3.5 py-2.5 text-sm"
			/>
		</div>

		<div class="grid grid-cols-2 gap-4">
			<div class="space-y-1.5">
				<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Model *</label>
				<select bind:value={model} class="auth-input w-full rounded-lg px-3.5 py-2.5 text-sm">
					{#each agentUi.models as m (m.value)}
						<option value={m.value}>{m.label}</option>
					{/each}
				</select>
			</div>
			<div class="space-y-1.5">
				<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
					Temperature — <span class="font-mono text-blue-400">{temperature.toFixed(1)}</span>
				</label>
				<input
					type="range"
					bind:value={temperature}
					min="0" max="2" step="0.1"
					class="mt-3 w-full accent-blue-500"
				/>
			</div>
		</div>

	</div>

	<div class="rounded-xl p-6 space-y-3" style="background:var(--surface);border:1px solid var(--ds-border)">
		<div>
			<h2 class="font-display text-sm font-semibold" style="color:var(--text-main)">Instructions *</h2>
			<p class="mt-0.5 text-xs text-muted-foreground">Base identity and behaviour for this agent</p>
		</div>
		<textarea
			bind:value={core_prompt}
			placeholder="You are a helpful assistant..."
			rows="8"
			class="auth-input w-full resize-y rounded-lg px-3.5 py-2.5 text-sm font-mono leading-relaxed"
		></textarea>
	</div>

	<div class="flex justify-end gap-3">
		<a
			href="{appBase}/instances"
			class="rounded-lg px-4 py-2.5 text-sm font-semibold text-muted-foreground transition-colors hover:text-foreground"
		>
			Cancel
		</a>
		<button
			type="submit"
			disabled={loading}
			class="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:opacity-60"
		>
			<Bot class="h-4 w-4" />
			{loading ? 'Creating...' : 'Create Agent'}
		</button>
	</div>
	</div>
</form>
