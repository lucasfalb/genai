<script lang="ts">
	import { aiSettingsApi } from '$lib/api/aiSettings';
	import { getErrorMessage } from '$lib/api/client';
	import type { TenantProvidersResponse } from '$lib/api/types';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { toast } from 'svelte-sonner';
	import Pencil from '@lucide/svelte/icons/pencil';
	import Save from '@lucide/svelte/icons/save';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Search from '@lucide/svelte/icons/search';
	import Eye from '@lucide/svelte/icons/eye';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import X from '@lucide/svelte/icons/x';
	import { Spinner } from '$lib/components/ui/spinner/index.js';

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
	let searchQuery = $state('');

	const filteredProviders = $derived(
		PROVIDERS.filter((p) => p.label.toLowerCase().includes(searchQuery.toLowerCase()))
	);

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
			toast.success(`${PROVIDERS.find((p) => p.value === providerValue)?.label} ${!current.enabled ? 'enabled' : 'disabled'}.`);
		} catch (err) {
			toast.error(getErrorMessage(err, 'Toggle failed.'));
		}
	}

	async function confirmRemove() {
		if (!deleteTarget) return;
		const provider = PROVIDERS.find((p) => p.value === deleteTarget);
		deleting = deleteTarget;
		const target = deleteTarget;
		deleteTarget = null;
		try {
			await aiSettingsApi.delete(target);
			config = await aiSettingsApi.get();
			apiKeys[target] = '';
			editing[target] = false;
			toast.success(`${provider?.label} configuration removed.`);
		} catch (err) {
			toast.error(getErrorMessage(err, 'Delete failed.'));
		} finally {
			deleting = null;
		}
	}

	function isProviderConfigured(providerValue: string): boolean {
		return config?.providers.some((p) => p.name === providerValue && p.has_api_key) ?? false;
	}

	function getProviderInfo(providerValue: string) {
		return config?.providers.find((p) => p.name === providerValue) ?? null;
	}
</script>

<div class="flex flex-col gap-4 p-4">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div class="relative w-full max-w-xs">
			<Search class="absolute top-2.5 left-2.5 h-4 w-4 text-muted-foreground" />
			<Input placeholder="Search providers..." bind:value={searchQuery} class="h-9 bg-background pl-9" />
		</div>
	</div>

	<div class="overflow-hidden border bg-card">
		<Table.Root containerClass="scrollbar-none bg-card" class="w-full table-fixed">
			<Table.Header class="bg-background">
				<Table.Row class="bg-background hover:bg-background">
					<Table.Head class="w-[200px] bg-background py-2 text-[11px] font-bold tracking-wider uppercase">Provider</Table.Head>
					<Table.Head class="bg-background py-2 text-[11px] font-bold tracking-wider uppercase">API Configuration</Table.Head>
					<Table.Head class="w-[100px] bg-background py-2 text-[11px] font-bold tracking-wider uppercase">Status</Table.Head>
					<Table.Head class="w-[100px] bg-background py-2"></Table.Head>
				</Table.Row>
			</Table.Header>

			<Table.Body>
				{#if filteredProviders.length === 0}
					<Table.Row class="bg-card hover:bg-card">
						<Table.Cell colspan={4} class="h-32 text-center text-muted-foreground">
							<div class="flex flex-col items-center gap-1">
								<span class="text-sm font-medium text-foreground">No providers found</span>
								<span class="text-xs">Try adjusting your search query.</span>
							</div>
						</Table.Cell>
					</Table.Row>
				{:else}
					{#each filteredProviders as provider (provider.value)}
						{@const provInfo = getProviderInfo(provider.value)}
						{@const isConfigured = isProviderConfigured(provider.value)}
						{@const isEditing = editing[provider.value] || !isConfigured}
						{@const isBusy = saving === provider.value || deleting === provider.value}

						<Table.Row class="group bg-card transition-colors hover:bg-muted/30">
							<Table.Cell class="py-3">
								<div class="flex items-center gap-3 overflow-hidden">
									<div
										class="flex h-9 w-9 shrink-0 items-center justify-center border bg-background p-1.5 transition-all group-hover:border-primary/40"
										style="background:color-mix(in srgb, {provider.color} 10%, transparent)"
									>
										<img src={provider.logo} alt={provider.label} class="h-full w-full object-contain" />
									</div>
									<div class="min-w-0">
										<p class="truncate text-sm font-semibold">{provider.label}</p>
										<p class="truncate text-[10px] text-muted-foreground uppercase tracking-tighter">
											{isConfigured ? 'Configured' : 'Not configured'}
										</p>
									</div>
								</div>
							</Table.Cell>

							<Table.Cell class="py-3">
								<div class="flex items-center gap-2">
									<div class="relative flex-1 max-w-md">
										<Input
											type={showKey[provider.value] ? 'text' : 'password'}
											bind:value={apiKeys[provider.value]}
											placeholder={isConfigured ? provInfo?.api_key_hint : 'Enter API Key'}
											disabled={!isEditing || isBusy}
											class="h-8 w-full bg-background font-mono text-xs pr-8"
										/>
										{#if isEditing}
											<button
												type="button"
												onclick={() => (showKey[provider.value] = !showKey[provider.value])}
												class="absolute right-1 top-1/2 -translate-y-1/2 flex h-6 w-6 items-center justify-center text-muted-foreground hover:text-foreground"
												tabindex="-1"
											>
												{#if showKey[provider.value]}
													<EyeOff class="h-3.5 w-3.5" />
												{:else}
													<Eye class="h-3.5 w-3.5" />
												{/if}
											</button>
										{/if}
									</div>
									
									{#if isConfigured && !editing[provider.value]}
										<Button
											variant="ghost"
											size="icon-sm"
											onclick={() => (editing[provider.value] = true)}
											disabled={isBusy}
											class="h-8 w-8"
										>
											<Pencil class="h-3.5 w-3.5" />
										</Button>
									{:else if isEditing}
										<div class="flex items-center gap-1">
											<Button
												variant="ghost"
												size="icon-sm"
												onclick={() => {
													editing[provider.value] = false;
													apiKeys[provider.value] = '';
												}}
												disabled={isBusy}
												class="h-8 w-8 text-muted-foreground"
											>
												<X class="h-3.5 w-3.5" />
											</Button>
											<Button
												variant="default"
												size="icon-sm"
												onclick={() => saveProvider(provider)}
												disabled={isBusy || !apiKeys[provider.value]?.trim()}
												class="h-8 w-8"
											>
												{#if saving === provider.value}
													<Spinner class="h-3.5 w-3.5" />
												{:else}
													<Save class="h-3.5 w-3.5" />
												{/if}
											</Button>
										</div>
									{/if}
								</div>
							</Table.Cell>

							<Table.Cell class="py-3">
								{#if isConfigured}
									<Switch
										checked={provInfo?.enabled}
										onCheckedChange={() => toggleProvider(provider.value)}
										disabled={isBusy}
									/>
								{:else}
									<span class="text-[10px] text-muted-foreground uppercase font-medium">—</span>
								{/if}
							</Table.Cell>

							<Table.Cell class="py-3 text-right">
								{#if isConfigured}
									<Button
										variant="ghost"
										size="icon-sm"
										onclick={() => (deleteTarget = provider.value)}
										disabled={isBusy}
										class="h-8 w-8 text-red-400 hover:bg-red-400/10 hover:text-red-400"
									>
										{#if deleting === provider.value}
											<Spinner class="h-3.5 w-3.5" />
										{:else}
											<Trash2 class="h-3.5 w-3.5" />
										{/if}
									</Button>
								{/if}
							</Table.Cell>
						</Table.Row>
					{/each}
				{/if}
			</Table.Body>
		</Table.Root>
		<div class="border-t bg-card px-4 py-2">
			<p class="text-[10px] font-bold tracking-widest text-muted-foreground uppercase">
				Showing {filteredProviders.length} of {PROVIDERS.length} providers
			</p>
		</div>
	</div>
</div>

<AlertDialog.Root
	open={deleteTarget !== null}
	onOpenChange={(o) => {
		if (!o) deleteTarget = null;
	}}
>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Remove provider</AlertDialog.Title>
			<AlertDialog.Description>
				Are you sure you want to remove the configuration for <strong class="text-foreground"
					>{PROVIDERS.find((p) => p.value === deleteTarget)?.label}</strong
				>?
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>Cancel</AlertDialog.Cancel>
			<Button variant="destructive" onclick={confirmRemove}>Remove</Button>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>

<style>
	:global(td) {
		white-space: nowrap;
	}
</style>
