<script lang="ts">
	import { aiSettingsApi } from '$lib/api/aiSettings';
	import { getErrorMessage } from '$lib/api/client';
	import type { TenantAIConfigResponse } from '$lib/api/types';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { toast } from 'svelte-sonner';
	import Cpu from '@lucide/svelte/icons/cpu';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import KeyRound from '@lucide/svelte/icons/key-round';

	let { data } = $props();

	const PROVIDERS = ['openai', 'azure', 'anthropic', 'cohere', 'mistral', 'groq'];

	let config = $state<TenantAIConfigResponse | null>(data.config);
	let provider = $state(data.config?.provider ?? 'openai');
	let apiKey = $state('');
	let defaultModel = $state(data.config?.default_model ?? '');
	let enabled = $state(data.config?.enabled ?? true);
	let saving = $state(false);
	let deleting = $state(false);

	const hasConfig = $derived(config?.provider != null);
	const hasApiKey = $derived(config?.has_api_key ?? false);

	async function save() {
		if (!apiKey.trim()) {
			toast.error('API key is required to save changes.');
			return;
		}
		saving = true;
		try {
			const updated = await aiSettingsApi.save({
				provider,
				api_key: apiKey.trim(),
				default_model: defaultModel.trim() || null,
				enabled
			});
			config = updated;
			apiKey = '';
			toast.success('AI configuration saved.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Save failed.'));
		} finally {
			saving = false;
		}
	}

	async function deleteConfig() {
		if (
			!confirm(
				'Remove AI configuration? The tenant will fall back to the platform default provider.'
			)
		)
			return;
		deleting = true;
		try {
			await aiSettingsApi.delete();
			config = null;
			provider = 'openai';
			apiKey = '';
			defaultModel = '';
			enabled = true;
			toast.success('AI configuration removed.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Delete failed.'));
		} finally {
			deleting = false;
		}
	}
</script>

<div class="mx-auto max-w-2xl space-y-6 p-6">
	<div class="flex items-center justify-between gap-4">
		<div>
			<h1 class="font-display text-xl font-semibold" style="color:var(--text-main)">AI Settings</h1>
			<p class="mt-1 text-sm text-muted-foreground">Configure a custom AI provider for this tenant</p>
		</div>
		<div class="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
			<Cpu class="h-5 w-5" />
		</div>
	</div>

	<!-- Status card -->
	<div class="rounded-xl p-4" style="background:var(--surface);border:1px solid var(--ds-border)">
		<div class="flex items-center justify-between gap-4">
			<div class="flex items-center gap-3">
				<div
					class="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-800"
					style="border:1px solid var(--ds-border-hover)"
				>
					<KeyRound class="h-4 w-4 text-muted-foreground" />
				</div>
				<div>
					<p class="text-sm font-medium" style="color:var(--text-main)">API Key</p>
					{#if config?.configured_by}
						<p class="text-xs text-muted-foreground">Configured by {config.configured_by}</p>
					{/if}
				</div>
			</div>
			{#if hasApiKey}
				<span
					class="inline-flex items-center gap-1.5 rounded-full bg-green-500/10 px-2.5 py-1 text-xs font-semibold text-green-400"
					style="border:1px solid rgba(74,222,128,0.2)"
				>
					<span class="h-1.5 w-1.5 rounded-full bg-green-400"></span>
					Key configured
				</span>
			{:else}
				<span
					class="inline-flex items-center gap-1.5 rounded-full bg-slate-500/10 px-2.5 py-1 text-xs font-semibold text-muted-foreground"
					style="border:1px solid var(--ds-border)"
				>
					<span class="h-1.5 w-1.5 rounded-full bg-slate-500"></span>
					No key
				</span>
			{/if}
		</div>
		{#if !hasConfig}
			<p
				class="mt-3 rounded-lg bg-blue-500/5 px-3 py-2 text-xs text-blue-300"
				style="border:1px solid rgba(59,130,246,0.15)"
			>
				No custom AI configuration. This tenant uses the platform default provider.
			</p>
		{/if}
	</div>

	<!-- Form card -->
	<div class="space-y-5 rounded-xl p-6" style="background:var(--surface);border:1px solid var(--ds-border)">
		<h2 class="text-sm font-semibold" style="color:var(--text-main)">Provider Configuration</h2>

		<div class="space-y-1.5">
			<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground"
				>Provider</label
			>
			<select bind:value={provider} class="auth-input w-full rounded-lg px-3.5 py-2.5 text-sm">
				{#each PROVIDERS as p (p)}
					<option value={p}>{p}</option>
				{/each}
			</select>
		</div>

		<div class="space-y-1.5">
			<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
				API Key
				{#if hasApiKey}
					<span class="ml-1 text-[10px] font-normal text-amber-400">— re-enter to save</span>
				{/if}
			</label>
			<input
				type="password"
				bind:value={apiKey}
				placeholder={hasApiKey ? 'Enter key to update settings' : 'sk-...'}
				class="auth-input w-full rounded-lg px-3.5 py-2.5 font-mono text-sm"
			/>
			<p class="text-[11px] text-muted-foreground">
				{#if hasApiKey}
					The stored key is not retrievable. You must re-enter it to save any changes.
				{:else}
					Your API key for the selected provider.
				{/if}
			</p>
		</div>

		<div class="space-y-1.5">
			<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground"
				>Default Model</label
			>
			<input
				type="text"
				bind:value={defaultModel}
				placeholder="gpt-4o-mini"
				class="auth-input w-full rounded-lg px-3.5 py-2.5 font-mono text-sm"
			/>
		</div>

		<div
			class="flex items-center justify-between rounded-lg px-3.5 py-3"
			style="background:var(--surface-hover);border:1px solid var(--ds-border)"
		>
			<div>
				<p class="text-sm font-medium" style="color:var(--text-main)">Enabled</p>
				<p class="text-xs text-muted-foreground">
					Use this custom provider instead of the platform default
				</p>
			</div>
			<Switch bind:checked={enabled} />
		</div>

		<div class="flex items-center justify-between gap-4 pt-2">
			{#if hasConfig}
				<button
					onclick={deleteConfig}
					disabled={deleting || saving}
					class="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold text-red-400 transition-colors hover:bg-red-400/10 disabled:cursor-not-allowed disabled:opacity-40"
				>
					<Trash2 class="h-4 w-4" />
					{deleting ? 'Removing...' : 'Remove Configuration'}
				</button>
			{:else}
				<div></div>
			{/if}

			<button
				onclick={save}
				disabled={saving || deleting}
				class="inline-flex items-center gap-2 rounded-lg px-5 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-40"
				style="background:var(--text-main);color:var(--canvas)"
			>
				{saving ? 'Saving...' : 'Save Configuration'}
			</button>
		</div>
	</div>
</div>
