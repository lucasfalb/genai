<script lang="ts">
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { superadminApi } from '$lib/api/superadmin';
	import { getErrorMessage } from '$lib/api/client';
	import type { SystemSettingsResponse } from '$lib/api/types';
	import { defaultAgentUiPublicSettings } from '$lib/settings/agent-ui';
	import { toast } from 'svelte-sonner';
	import Settings from '@lucide/svelte/icons/settings';
	import KeyRound from '@lucide/svelte/icons/key-round';

	let { data } = $props();

	let settings = $state<SystemSettingsResponse>(data.settings);
	let busy = $state(false);

	// Platform
	let platformName = $state(settings.platform_name ?? '');
	let platformUrl = $state(settings.platform_public_url ?? '');
	let platformLogo = $state(settings.platform_logo_url ?? '');
	let maintenanceMode = $state(settings.maintenance_mode ?? false);
	let registrationEnabled = $state(settings.registration_enabled ?? true);

	// SMTP
	let smtpHost = $state(settings.smtp_host ?? '');
	let smtpPort = $state(settings.smtp_port ?? 587);
	let smtpSecure = $state(settings.smtp_secure ?? false);
	let smtpUser = $state(settings.smtp_user ?? '');
	let smtpFrom = $state(settings.smtp_from ?? '');
	let smtpPass = $state('');

	// AI
	let aiProvider = $state(settings.ai_provider ?? 'openai');
	let aiModel = $state(settings.ai_default_model ?? '');
	let aiApiKey = $state('');
	let agentUiJson = $state(
		JSON.stringify(settings.public_settings?.agent_ui ?? defaultAgentUiPublicSettings().agent_ui, null, 2)
	);

	const AI_PROVIDERS = ['openai', 'azure', 'anthropic', 'cohere', 'mistral', 'groq'];

	async function save() {
		busy = true;
		try {
			let agentUiSettings: unknown;
			try {
				agentUiSettings = JSON.parse(agentUiJson || '{}');
			} catch {
				toast.error('Agent UI settings must be valid JSON.');
				return;
			}

			const updated = await superadminApi.updateSettings({
				platform_name: platformName || undefined,
				platform_public_url: platformUrl || undefined,
				platform_logo_url: platformLogo || undefined,
				maintenance_mode: maintenanceMode,
				registration_enabled: registrationEnabled,
				smtp_host: smtpHost || undefined,
				smtp_port: smtpPort || undefined,
				smtp_secure: smtpSecure,
				smtp_user: smtpUser || undefined,
				smtp_from: smtpFrom || undefined,
				smtp_pass: smtpPass || undefined,
				ai_provider: aiProvider || undefined,
				ai_default_model: aiModel || undefined,
				ai_api_key: aiApiKey || undefined,
				public_settings: {
					...(settings.public_settings ?? {}),
					agent_ui: agentUiSettings
				}
			});
			settings = updated;
			agentUiJson = JSON.stringify(settings.public_settings?.agent_ui ?? defaultAgentUiPublicSettings().agent_ui, null, 2);
			smtpPass = '';
			aiApiKey = '';
			toast.success('Settings saved.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Save failed.'));
		} finally {
			busy = false;
		}
	}

	function section(label: string) {
		return label;
	}
</script>

<div class="space-y-6 p-6">
	<div class="flex items-center gap-3">
		<div class="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
			<Settings class="h-4 w-4" />
		</div>
		<div>
			<h1 class="font-display text-lg font-semibold" style="color:var(--text-main)">System Settings</h1>
			<p class="text-xs text-muted-foreground">Global platform configuration</p>
		</div>
	</div>

	<!-- Platform section -->
	<div class="rounded-xl p-5 space-y-4" style="background:var(--surface);border:1px solid var(--ds-border)">
		<h2 class="text-xs font-semibold uppercase tracking-widest text-muted-foreground">{section('Platform')}</h2>

		<div class="grid grid-cols-2 gap-4">
			<div class="space-y-1">
				<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Platform Name</label>
				<input bind:value={platformName} placeholder="GenAI Platform" class="auth-input w-full rounded-lg px-3 py-2 text-sm" />
			</div>
			<div class="space-y-1">
				<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Public URL</label>
				<input bind:value={platformUrl} placeholder="https://app.example.com" class="auth-input w-full rounded-lg px-3 py-2 text-sm" />
			</div>
			<div class="col-span-2 space-y-1">
				<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Logo URL</label>
				<input bind:value={platformLogo} placeholder="https://..." class="auth-input w-full rounded-lg px-3 py-2 text-sm" />
			</div>
		</div>

		<div class="grid grid-cols-2 gap-4">
			<div class="flex items-center justify-between rounded-lg px-3.5 py-3" style="background:var(--surface-hover);border:1px solid var(--ds-border)">
				<div>
					<p class="text-sm" style="color:var(--text-main)">Maintenance Mode</p>
					<p class="text-xs text-muted-foreground">Blocks all requests</p>
				</div>
				<Switch bind:checked={maintenanceMode} />
			</div>
			<div class="flex items-center justify-between rounded-lg px-3.5 py-3" style="background:var(--surface-hover);border:1px solid var(--ds-border)">
				<div>
					<p class="text-sm" style="color:var(--text-main)">Registration</p>
					<p class="text-xs text-muted-foreground">Allow new signups</p>
				</div>
				<Switch bind:checked={registrationEnabled} />
			</div>
		</div>
	</div>

	<!-- SMTP section -->
	<div class="rounded-xl p-5 space-y-4" style="background:var(--surface);border:1px solid var(--ds-border)">
		<div class="flex items-center justify-between">
			<h2 class="text-xs font-semibold uppercase tracking-widest text-muted-foreground">{section('SMTP')}</h2>
			{#if settings.has_smtp_pass}
				<span class="inline-flex items-center gap-1.5 rounded-full bg-green-500/10 px-2.5 py-1 text-xs font-semibold text-green-400" style="border:1px solid rgba(74,222,128,0.2)">
					<KeyRound class="h-3 w-3" />
					Password configured
				</span>
			{:else}
				<span class="inline-flex items-center gap-1.5 rounded-full bg-slate-500/10 px-2.5 py-1 text-xs font-semibold text-muted-foreground" style="border:1px solid var(--ds-border)">
					No password
				</span>
			{/if}
		</div>

		<div class="grid grid-cols-3 gap-4">
			<div class="col-span-2 space-y-1">
				<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Host</label>
				<input bind:value={smtpHost} placeholder="smtp.example.com" class="auth-input w-full rounded-lg px-3 py-2 text-sm" />
			</div>
			<div class="space-y-1">
				<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Port</label>
				<input bind:value={smtpPort} type="number" class="auth-input w-full rounded-lg px-3 py-2 text-sm" />
			</div>
			<div class="space-y-1">
				<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">User</label>
				<input bind:value={smtpUser} placeholder="smtp@example.com" class="auth-input w-full rounded-lg px-3 py-2 text-sm" />
			</div>
			<div class="space-y-1">
				<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">From</label>
				<input bind:value={smtpFrom} placeholder="noreply@example.com" class="auth-input w-full rounded-lg px-3 py-2 text-sm" />
			</div>
			<div class="space-y-1">
				<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
					Password {#if settings.has_smtp_pass}<span class="text-[10px] font-normal text-amber-400">— re-enter to update</span>{/if}
				</label>
				<input type="password" bind:value={smtpPass} placeholder={settings.has_smtp_pass ? 'Enter to update' : ''} class="auth-input w-full rounded-lg px-3 py-2 font-mono text-sm" />
			</div>
		</div>

		<div class="flex items-center justify-between rounded-lg px-3.5 py-3" style="background:var(--surface-hover);border:1px solid var(--ds-border)">
			<p class="text-sm" style="color:var(--text-main)">TLS / Secure</p>
			<Switch bind:checked={smtpSecure} />
		</div>
	</div>

	<!-- AI section -->
	<div class="rounded-xl p-5 space-y-4" style="background:var(--surface);border:1px solid var(--ds-border)">
		<div class="flex items-center justify-between">
			<h2 class="text-xs font-semibold uppercase tracking-widest text-muted-foreground">{section('AI Config (Platform Default)')}</h2>
			{#if settings.has_ai_api_key}
				<span class="inline-flex items-center gap-1.5 rounded-full bg-green-500/10 px-2.5 py-1 text-xs font-semibold text-green-400" style="border:1px solid rgba(74,222,128,0.2)">
					<KeyRound class="h-3 w-3" />
					Key configured
				</span>
			{:else}
				<span class="inline-flex items-center gap-1.5 rounded-full bg-slate-500/10 px-2.5 py-1 text-xs font-semibold text-muted-foreground" style="border:1px solid var(--ds-border)">
					No key
				</span>
			{/if}
		</div>

		<div class="grid grid-cols-3 gap-4">
			<div class="space-y-1">
				<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Provider</label>
				<select bind:value={aiProvider} class="auth-input w-full rounded-lg px-3 py-2 text-sm">
					{#each AI_PROVIDERS as p (p)}<option value={p}>{p}</option>{/each}
				</select>
			</div>
			<div class="space-y-1">
				<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Default Model</label>
				<input bind:value={aiModel} placeholder="gpt-4o-mini" class="auth-input w-full rounded-lg px-3 py-2 font-mono text-sm" />
			</div>
			<div class="space-y-1">
				<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
					API Key {#if settings.has_ai_api_key}<span class="text-[10px] font-normal text-amber-400">— re-enter to update</span>{/if}
				</label>
				<input type="password" bind:value={aiApiKey} placeholder={settings.has_ai_api_key ? 'Enter to update' : 'sk-...'} class="auth-input w-full rounded-lg px-3 py-2 font-mono text-sm" />
			</div>
		</div>
	</div>

	<!-- Agent UI section -->
	<div class="rounded-xl p-5 space-y-4" style="background:var(--surface);border:1px solid var(--ds-border)">
		<div class="flex items-start justify-between gap-4">
			<div>
				<h2 class="text-xs font-semibold uppercase tracking-widest text-muted-foreground">{section('Agent UI Defaults')}</h2>
				<p class="mt-1 text-xs text-muted-foreground">Public custom settings loaded by the tenant agent creation and detail screens.</p>
			</div>
			<button
				type="button"
				onclick={() => { agentUiJson = JSON.stringify(defaultAgentUiPublicSettings().agent_ui, null, 2); }}
				class="rounded-lg border px-3 py-1.5 text-xs font-semibold transition-colors hover:bg-[var(--surface-hover)]"
				style="border-color:var(--ds-border)"
			>
				Reset defaults
			</button>
		</div>

		<div class="space-y-1">
			<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">public_settings.agent_ui</label>
			<textarea
				bind:value={agentUiJson}
				rows="18"
				spellcheck="false"
				class="auth-input w-full resize-y rounded-lg px-3 py-2 font-mono text-xs leading-relaxed"
			></textarea>
			<p class="text-xs text-muted-foreground">
				Controls available models, default model, creation templates and the agent test panel.
			</p>
		</div>
	</div>

	<div class="flex justify-end">
		<button
			onclick={save}
			disabled={busy}
			class="rounded-lg px-5 py-2 text-sm font-semibold disabled:opacity-40"
			style="background:var(--text-main);color:var(--canvas)"
		>
			{busy ? 'Saving...' : 'Save Settings'}
		</button>
	</div>
</div>
