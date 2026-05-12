<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Check from '@lucide/svelte/icons/check';
	import ChevronsUpDown from '@lucide/svelte/icons/chevrons-up-down';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import * as Command from '$lib/components/ui/command/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import { cn } from '$lib/utils.js';
	import KnowledgeCard from '$lib/components/instance/knowledge-card.svelte';
	import { instancesApi } from '$lib/api/instances';
	import { aiSettingsApi } from '$lib/api/aiSettings';
	import { getErrorMessage } from '$lib/api/client';
	import { getAgentUiSettings, inferProviderFromModel } from '$lib/settings/agent-ui';
	import type { AgentInstanceResponse, TenantProvidersResponse } from '$lib/api/types';

	let { data } = $props();

	const { register, unregister, setSaving } = getContext<{
		register: (handler: () => Promise<void>, label: string) => void;
		unregister: () => void;
		setSaving: (v: boolean) => void;
	}>('save-action');

	const agentUi = getAgentUiSettings(data.publicSettings);

	let instance = $state<AgentInstanceResponse>(data.instance);
	let name = $state(data.instance.name);
	let description = $state(data.instance.description ?? '');
	let core_prompt = $state(data.instance.core_prompt);
	let model = $state(data.instance.model);
	let temperature = $state(data.instance.temperature);
	let ragScope = $state<string[]>(data.instance.rag_scope ?? []);
	let validationError = $state('');

	let tenantProviders = $state<TenantProvidersResponse | null>(null);
	let provider = $state('');
	let modelsList = $state<string[]>([]);
	let modelsLoading = $state(false);

	let providerComboboxOpen = $state(false);
	let modelComboboxOpen = $state(false);
	let providerTriggerRef = $state<HTMLButtonElement>(null!);
	let modelTriggerRef = $state<HTMLButtonElement>(null!);

	const availableProviders = $derived.by(() => {
		if (!tenantProviders) return [];
		const configuredNames = new Set(
			tenantProviders.providers.filter((p) => p.has_api_key && p.enabled).map((p) => p.name)
		);
		return agentUi.providers.filter((p) => configuredNames.has(p.value));
	});

	const selectedProviderLabel = $derived(
		availableProviders.find((p) => p.value === provider)?.label ?? 'Select provider...'
	);

	const selectedModelLabel = $derived(model || 'Select a model...');

	async function loadTenantProviders() {
		try {
			tenantProviders = await aiSettingsApi.get();
		} catch {
			tenantProviders = null;
		}
	}

	async function fetchModels() {
		if (!provider) return;
		modelsLoading = true;
		modelsList = [];
		try {
			const res = await aiSettingsApi.getModels(provider);
			modelsList = res.models.map((m) => m.id);
			if (modelsList.length > 0 && !modelsList.includes(model)) {
				model = modelsList[0];
			}
		} catch (err) {
			toast.error(getErrorMessage(err, `Failed to load models for ${provider}`));
		} finally {
			modelsLoading = false;
		}
	}

	function onProviderSelect(newProvider: string) {
		provider = newProvider;
		providerComboboxOpen = false;
		model = '';
		modelsList = [];
		tick().then(() => {
			providerTriggerRef?.focus();
		});
		fetchModels();
	}

	function closeAndFocusTrigger(ref: HTMLButtonElement | null) {
		modelComboboxOpen = false;
		tick().then(() => {
			ref?.focus();
		});
	}

	$effect(() => {
		if (model && provider) return;
		if (!tenantProviders) return;
		if (availableProviders.length === 0) return;

		const detected = agentUi.providers.find((p) => p.models.some((m) => m.value === model));
		if (detected && availableProviders.some((p) => p.value === detected.value)) {
			provider = detected.value;
			fetchModels();
			return;
		}
		const inferred = inferProviderFromModel(model);
		if (inferred && availableProviders.some((p) => p.value === inferred)) {
			provider = inferred;
			fetchModels();
			return;
		}
		if (!provider && availableProviders.length > 0) {
			provider = availableProviders[0].value;
			fetchModels();
		}
	});

	async function saveConfig() {
		validationError = '';
		if (!name.trim()) {
			validationError = 'Name is required.';
			return;
		}
		if (!core_prompt.trim()) {
			validationError = 'Core prompt is required.';
			return;
		}
		if (!model) {
			validationError = 'Model is required.';
			return;
		}
		if (temperature < 0 || temperature > 2) {
			validationError = 'Temperature must be between 0 and 2.';
			return;
		}
		setSaving(true);
		try {
			instance = await instancesApi.update(instance.id, {
				name: name.trim(),
				description: description.trim() || undefined,
				core_prompt: core_prompt.trim(),
				model,
				temperature,
				rag_scope: ragScope
			});
			toast.success('Agent saved.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Save failed.'));
		} finally {
			setSaving(false);
		}
	}

	onMount(() => {
		loadTenantProviders();
		register(saveConfig, 'Save changes');
		return () => unregister();
	});
</script>

<div class="scrollbar-none mx-auto max-w-5xl space-y-5 px-6 py-5">
	{#if validationError}
		<div
			class="rounded-lg px-4 py-3 text-sm text-red-400"
			style="background:color-mix(in srgb,red 8%,transparent);border:1px solid color-mix(in srgb,red 18%,transparent)"
		>
			{validationError}
		</div>
	{/if}

	<div class="space-y-5 rounded-lg border border-ds-border bg-surface p-6">
		<div class="flex items-center justify-between">
			<div>
				<h2 class="font-display text-sm font-semibold text-text-main">Details</h2>
				<p class="mt-1 text-xs text-muted-foreground">
					Agent identity, description and runtime model.
				</p>
			</div>
			<Badge variant="outline" class="text-[10px] uppercase">{instance.status}</Badge>
		</div>

		<div class="space-y-1.5">
			<label class="block text-[11px] font-semibold tracking-widest text-muted-foreground uppercase"
				>Name *</label
			>
			<Input bind:value={name} placeholder="Agent name" />
		</div>

		<div class="space-y-1.5">
			<label class="block text-[11px] font-semibold tracking-widest text-muted-foreground uppercase"
				>Description</label
			>
			<Input bind:value={description} placeholder="Short description" />
		</div>

		<div class="grid grid-cols-2 gap-4">
			<div class="space-y-1.5">
				<label
					class="block text-[11px] font-semibold tracking-widest text-muted-foreground uppercase"
					>Provider *</label
				>
				<Popover.Root bind:open={providerComboboxOpen}>
					<Popover.Trigger bind:ref={providerTriggerRef}>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="outline"
								class="w-full justify-between"
								role="combobox"
								aria-expanded={providerComboboxOpen}
							>
								<span class="truncate">{selectedProviderLabel}</span>
								<ChevronsUpDown class="size-4 shrink-0 opacity-50" />
							</Button>
						{/snippet}
					</Popover.Trigger>
					<Popover.Content class="p-0">
						<Command.Root>
							<Command.Input placeholder="Search provider..." />
							<Command.List>
								<Command.Empty>No providers.</Command.Empty>
								<Command.Group>
									{#each availableProviders as p (p.value)}
										<Command.Item value={p.label} onSelect={() => onProviderSelect(p.value)}>
											<Check class={cn('size-4', provider !== p.value && 'text-transparent')} />
											{p.label}
										</Command.Item>
									{/each}
								</Command.Group>
							</Command.List>
						</Command.Root>
					</Popover.Content>
				</Popover.Root>
			</div>

			<div class="space-y-1.5">
				<label
					class="block text-[11px] font-semibold tracking-widest text-muted-foreground uppercase"
					>Model *</label
				>
				{#if modelsLoading}
					<Button variant="outline" class="w-full justify-between" disabled>
						<span class="truncate">Loading models...</span>
						<Spinner class="size-4 shrink-0" />
					</Button>
				{:else}
					<Popover.Root bind:open={modelComboboxOpen}>
						<Popover.Trigger bind:ref={modelTriggerRef}>
							{#snippet child({ props })}
								<Button
									{...props}
									variant="outline"
									class="w-full justify-between"
									role="combobox"
									aria-expanded={modelComboboxOpen}
									disabled={!provider}
								>
									<span class="truncate">{selectedModelLabel}</span>
									<ChevronsUpDown class="size-4 shrink-0 opacity-50" />
								</Button>
							{/snippet}
						</Popover.Trigger>
						<Popover.Content class="p-0">
							<Command.Root>
								<Command.Input placeholder="Search model..." />
								<Command.List>
									<Command.Empty>No models found.</Command.Empty>
									<Command.Group>
										{#each modelsList as modelId (modelId)}
											<Command.Item
												value={modelId}
												onSelect={() => {
													model = modelId;
													closeAndFocusTrigger(modelTriggerRef);
												}}
											>
												<Check class={cn('size-4', model !== modelId && 'text-transparent')} />
												{modelId}
											</Command.Item>
										{/each}
									</Command.Group>
								</Command.List>
							</Command.Root>
						</Popover.Content>
					</Popover.Root>
				{/if}
			</div>
		</div>
	</div>

	<div class="space-y-3 rounded-lg border border-ds-border bg-surface p-6">
		<div>
			<h2 class="font-display text-sm font-semibold text-text-main">Instructions</h2>
			<p class="mt-1 text-xs text-muted-foreground">
				Base behavior for this agent. Topic-specific blocks live in the Instructions tab.
			</p>
		</div>
		<label class="block text-[11px] font-semibold tracking-widest text-muted-foreground uppercase"
			>Core prompt *</label
		>
		<Textarea
			bind:value={core_prompt}
			rows={10}
			class="resize-y font-mono leading-relaxed"
			placeholder="You are..."
		/>
	</div>

	<KnowledgeCard bind:ragScope />
</div>
