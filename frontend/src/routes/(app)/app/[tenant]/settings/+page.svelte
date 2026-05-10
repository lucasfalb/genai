<script lang="ts">
	import { aiSettingsApi } from '$lib/api/aiSettings';
	import { getErrorMessage } from '$lib/api/client';
	import type { TenantProvidersResponse } from '$lib/api/types';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Accordion from '$lib/components/ui/accordion/index.js';
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import { toast } from 'svelte-sonner';
	import Cpu from '@lucide/svelte/icons/cpu';
	import KeyRound from '@lucide/svelte/icons/key-round';
	import Eye from '@lucide/svelte/icons/eye';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import Pencil from '@lucide/svelte/icons/pencil';
	import Save from '@lucide/svelte/icons/save';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import { Switch } from '$lib/components/ui/switch/index.js';

	let { data } = $props();

	interface Provider {
		value: string;
		label: string;
		placeholder: string;
		description: string;
		logo: string;
		color: string;
	}

	const PROVIDERS: Provider[] = [
		{
			value: 'openai',
			label: 'OpenAI',
			placeholder: 'sk-proj-...',
			description: '',
			logo: 'https://www.svgrepo.com/show/306500/openai.svg',
			color: '#fff'
		},
		{
			value: 'anthropic',
			label: 'Anthropic',
			placeholder: 'sk-ant-api03-...',
			description: '',
			logo: 'https://cdn.simpleicons.org/anthropic/CA9982',
			color: '#CA9982'
		},
		{
			value: 'google',
			label: 'Google AI',
			placeholder: 'AIza...',
			description: '',
			logo: 'https://cdn.simpleicons.org/google/4285F4',
			color: '#4285F4'
		}
	];

	let config = $state<TenantProvidersResponse | null>(data.config);
	let apiKeys = $state<Record<string, string>>({});
	let saving = $state<string | null>(null);
	let deleting = $state<string | null>(null);
	let editing = $state<Record<string, boolean>>({});
	let showKey = $state<Record<string, boolean>>({});
	let deleteTarget = $state<string | null>(null);

	async function saveProvider(provider: Provider) {
		const apiKey = apiKeys[provider.value];
		if (!apiKey?.trim()) {
			toast.error('API key is required.');
			return;
		}

		saving = provider.value;
		try {
			const updated = await aiSettingsApi.save({
				name: provider.value,
				api_key: apiKey.trim()
			});
			config = updated;
			apiKeys[provider.value] = '';
			editing[provider.value] = false;
			toast.success(`${provider.label} configured successfully.`);
		} catch (err) {
			toast.error(getErrorMessage(err, 'Save failed.'));
		} finally {
			saving = null;
		}
	}

	async function toggleProvider(providerValue: string) {
		const current = config?.providers.find((p) => p.name === providerValue);
		if (!current?.has_api_key) return;
		try {
			const updated = await aiSettingsApi.save({
				name: providerValue,
				enabled: !current.enabled
			});
			config = updated;
		} catch (err) {
			toast.error(getErrorMessage(err, 'Toggle failed.'));
		}
	}

	async function confirmRemove() {
		if (!deleteTarget) return;
		const provider = PROVIDERS.find((p) => p.value === deleteTarget);
		deleting = deleteTarget;
		try {
			await aiSettingsApi.delete(deleteTarget);
			config = await aiSettingsApi.get();
			apiKeys = {};
			toast.success(`${provider?.label} configuration removed.`);
		} catch (err) {
			toast.error(getErrorMessage(err, 'Delete failed.'));
		} finally {
			deleting = null;
			deleteTarget = null;
		}
	}

	function isProviderConfigured(providerValue: string): boolean {
		return config?.providers.some((p) => p.name === providerValue && p.has_api_key) ?? false;
	}

	function getProviderInfo(providerValue: string) {
		return config?.providers.find((p) => p.name === providerValue) ?? null;
	}
</script>

<div class="mx-auto max-w-5xl space-y-8 p-8">
	<!-- Header -->
	<div class="space-y-4">
		<div class="flex items-center justify-between gap-4">
			<div class="flex items-center gap-4">
				<div
					class="flex h-16 w-16 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 text-blue-400 shadow-lg"
					style="border:1px solid var(--ds-border-hover)"
				>
					<Cpu class="h-8 w-8" />
				</div>
				<div>
					<h1 class="font-display text-3xl font-bold tracking-tight" style="color:var(--text-main)">
						AI Providers
					</h1>
					<p class="mt-1 text-sm text-muted-foreground">
						Configure and manage your AI provider integrations
					</p>
				</div>
			</div>
		</div>
	</div>

	<!-- Provider cards -->
	<div class="grid gap-4 md:grid-cols-1">
		{#each PROVIDERS as provider (provider.value)}
			{@const provInfo = getProviderInfo(provider.value)}
			<div
				class="overflow-hidden rounded-xl border transition-all hover:shadow-lg"
				style="background:var(--surface);border-color:var(--ds-border)"
			>
				<Accordion.Root type="single" collapsible>
					<Accordion.Item value={provider.value} class="border-0">
						<Accordion.Trigger class="px-6 py-5 hover:no-underline">
							<div class="flex flex-1 items-center justify-between pr-4 text-left">
								<div class="flex items-center gap-5">
									<!-- Logo -->
									<div
										class="flex h-14 w-14 items-center justify-center rounded-xl p-2.5"
										style="background:color-mix(in srgb, {provider.color} 10%, transparent);border:1px solid color-mix(in srgb, {provider.color} 20%, transparent)"
									>
										<img
											src={provider.logo}
											alt={provider.label}
											class="h-full w-full object-contain"
										/>
									</div>

									<!-- Info -->
									<div class="flex flex-col gap-1">
										<div class="flex items-center gap-2.5">
											<h3 class="text-base font-semibold" style="color:var(--text-main)">
												{provider.label}
											</h3>
										</div>
									</div>
								</div>

								<div class="flex items-center gap-3">
									{#if isProviderConfigured(provider.value)}
										<Switch
											checked={provInfo?.enabled}
											onCheckedChange={() => toggleProvider(provider.value)}
										/>
									{/if}
								</div>
							</div>
						</Accordion.Trigger>

						<Accordion.Content class="border-t px-6 py-5" style="border-color:var(--ds-border)">
							<div class="space-y-4">
								<!-- API Key -->
								<div class="space-y-2.5">
									<label
										class="flex items-center gap-2 text-[11px] font-semibold tracking-widest text-muted-foreground uppercase"
									>
										<KeyRound class="h-3.5 w-3.5" />
										API Key *
									</label>
									<div class="flex items-center gap-2">
										<div class="relative flex-1">
											<Input
												type={showKey[provider.value] ? 'text' : 'password'}
												bind:value={apiKeys[provider.value]}
												placeholder={isProviderConfigured(provider.value) ? provInfo?.api_key_hint : ''}
												disabled={isProviderConfigured(provider.value) && !editing[provider.value]}
												class="h-11 w-full font-mono text-sm pr-10"
												style="border-color:var(--ds-border)"
											/>
											{#if editing[provider.value]}
												<button
													type="button"
													onclick={() => { showKey[provider.value] = !showKey[provider.value]; }}
													class="absolute right-2 top-1/2 -translate-y-1/2 flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:text-foreground"
													tabindex="-1"
												>
													{#if showKey[provider.value]}
														<EyeOff class="h-4 w-4" />
													{:else}
														<Eye class="h-4 w-4" />
													{/if}
												</button>
											{/if}
										</div>
										{#if isProviderConfigured(provider.value)}
											<Button
												variant="ghost"
												size="icon"
												onclick={() => {
													if (editing[provider.value]) {
														apiKeys[provider.value] = '';
													}
													editing[provider.value] = !editing[provider.value];
												}}
												class="h-11 w-11 shrink-0"
												title="Edit"
											>
												<Pencil class="h-4 w-4" />
											</Button>
										{/if}
										{#if editing[provider.value] || !isProviderConfigured(provider.value)}
											<Button
												variant="default"
												size="icon"
												onclick={() => saveProvider(provider)}
												disabled={saving === provider.value || !apiKeys[provider.value]?.trim()}
												class="h-11 w-11 shrink-0"
												title="Save"
											>
												<Save class="h-4 w-4" />
											</Button>
										{/if}
										{#if isProviderConfigured(provider.value)}
											<Button
												variant="ghost"
												size="icon"
												onclick={() => { deleteTarget = provider.value; }}
												disabled={deleting === provider.value}
												class="h-11 w-11 shrink-0 text-red-400 hover:bg-red-500/20 hover:text-red-400"
												title="Remove"
											>
												<Trash2 class="h-4 w-4" />
											</Button>
										{/if}
									</div>
								</div>
							</div>
						</Accordion.Content>
					</Accordion.Item>
				</Accordion.Root>
			</div>
		{/each}
	</div>
</div>

<AlertDialog.Root open={deleteTarget !== null} onOpenChange={(o) => { if (!o) deleteTarget = null; }}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Remove provider</AlertDialog.Title>
			<AlertDialog.Description>
				{PROVIDERS.find((p) => p.value === deleteTarget)?.label} configuration will be removed.
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>Cancel</AlertDialog.Cancel>
			<AlertDialog.Action onclick={confirmRemove}>Remove</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
