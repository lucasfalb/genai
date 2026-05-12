<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import Bot from '@lucide/svelte/icons/bot';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import Check from '@lucide/svelte/icons/check';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import ChevronsUpDown from '@lucide/svelte/icons/chevrons-up-down';
	import { instancesApi } from '$lib/api/instances';
	import { aiSettingsApi } from '$lib/api/aiSettings';
	import { ApiError } from '$lib/api/client';
	import { tenantBaseFromPath } from '$lib/routes/tenant';
	import { getAgentUiSettings, inferProviderFromModel, type AgentTemplateOption } from '$lib/settings/agent-ui';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Textarea } from '$lib/components/ui/textarea';
	import { Label } from '$lib/components/ui/label';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import * as Command from '$lib/components/ui/command/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import { cn } from '$lib/utils.js';
	import type { TenantProvidersResponse } from '$lib/api/types';

	let { data } = $props();
	const agentUi = getAgentUiSettings(data.publicSettings);

	let name = $state('');
	let description = $state('');
	let core_prompt = $state('');
	let model = $state(agentUi.default_model);
	let loading = $state(false);
	let error = $state('');
	const appBase = $derived(tenantBaseFromPath(page.url.pathname));

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
			modelsList = [];
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

	onMount(() => {
		loadTenantProviders();
	});

	function applyTemplate(template: AgentTemplateOption) {
		name = template.name;
		description = template.description;
		core_prompt = template.core_prompt;
	}

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!name.trim()) {
			error = 'Name is required.';
			return;
		}
		if (!core_prompt.trim()) {
			error = 'Core prompt is required.';
			return;
		}
		if (!model) {
			error = 'Model is required.';
			return;
		}
		error = '';
		loading = true;
		try {
			const inst = await instancesApi.create({
				name: name.trim(),
				description: description.trim() || undefined,
				core_prompt: core_prompt.trim(),
				model,
				temperature: 0.7
			});
			await goto(`${appBase}/instances/${inst.id}`);
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Failed to create instance.';
		} finally {
			loading = false;
		}
	}
</script>

<div class="flex flex-col gap-4 px-6 pt-6 pb-12">
	<a
		href="{appBase}/instances"
		class="flex w-fit items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
	>
		<ChevronLeft class="h-3.5 w-3.5" />
		Back to Agents
	</a>

	<form
		onsubmit={handleSubmit}
		class="mx-auto grid w-full max-w-6xl gap-6 lg:grid-cols-[280px_1fr]"
	>
		{#if error}
			<div
				class="rounded-lg border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive lg:col-span-2"
			>
				{error}
			</div>
		{/if}

		<aside class="space-y-4">
			<div class="flex items-center gap-2 px-1">
				<Sparkles class="h-3.5 w-3.5 text-blue-500" />
				<h2 class="text-[10px] font-bold tracking-widest text-muted-foreground uppercase">
					Quick Templates
				</h2>
			</div>

			<div class="grid gap-2">
				{#each agentUi.templates as template (template.name)}
					<button
						type="button"
						onclick={() => applyTemplate(template)}
						class="group flex flex-col gap-1 rounded-xl border bg-card p-4 text-left transition-all hover:border-primary/40 hover:bg-muted/30"
					>
						<span
							class="text-sm font-semibold text-foreground transition-colors group-hover:text-primary"
						>
							{template.name}
						</span>
						<span class="line-clamp-2 text-[11px] leading-relaxed text-muted-foreground">
							{template.description}
						</span>
					</button>
				{/each}
			</div>
		</aside>

		<div class="flex flex-col gap-6">
			<div class="space-y-5 rounded-xl border bg-card p-6 shadow-sm">
				<div class="flex items-center gap-2">
					<Bot class="h-4 w-4 text-blue-500" />
					<h2 class="text-sm font-semibold text-foreground">Agent Configuration</h2>
				</div>
				<div class="flex flex-col gap-4">
					<div class="space-y-2">
						<Label
							for="name"
							class="text-[11px] font-bold tracking-wider text-muted-foreground uppercase"
							>Agent Name *</Label
						>
						<Input
							id="name"
							bind:value={name}
							placeholder="e.g. Sales Assistant"
							class="h-10 bg-background"
						/>
					</div>

					<div class="space-y-2">
						<Label
							class="text-[11px] font-bold tracking-wider text-muted-foreground uppercase"
							>Provider *</Label
						>
						<Popover.Root bind:open={providerComboboxOpen}>
							<Popover.Trigger bind:ref={providerTriggerRef}>
								{#snippet child({ props })}
									<Button
										{...props}
										variant="outline"
										class="h-10 w-full justify-between bg-background"
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

					<div class="space-y-2">
						<Label
							class="text-[11px] font-bold tracking-wider text-muted-foreground uppercase"
							>Model *</Label
						>
						{#if modelsLoading}
							<Button variant="outline" class="h-10 w-full justify-between bg-background" disabled>
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
											class="h-10 w-full justify-between bg-background"
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

				<div class="space-y-2">
					<Label
						for="desc"
						class="text-[11px] font-bold tracking-wider text-muted-foreground uppercase"
						>Description</Label
					>
					<Input
						id="desc"
						bind:value={description}
						placeholder="Short objective of this agent..."
						class="h-10 bg-background"
					/>
				</div>

			</div>

			<div class="space-y-4 rounded-xl border bg-card p-6 shadow-sm">
				<div class="flex items-center gap-2">
					<Bot class="h-4 w-4 text-blue-500" />
					<h2 class="text-sm font-semibold text-foreground">System Prompt</h2>
				</div>
				<p class="text-xs text-muted-foreground/60">
					Instructions that define how the agent behaves and responds.
				</p>
				<Textarea
					id="prompt"
					bind:value={core_prompt}
					placeholder="Enter agent instructions here..."
					class="min-h-[300px] resize-none bg-background font-mono text-sm leading-relaxed focus-visible:ring-1"
				/>
			</div>

			<div class="flex items-center justify-end gap-3">
				<Button variant="ghost" href="{appBase}/instances" class="font-medium">Cancel</Button>
				<Button type="submit" disabled={loading} class="min-w-[140px] gap-2">
					{#if loading}
						<span
							class="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent"
						></span>
						Creating...
					{:else}
						<Bot class="h-4 w-4" />
						Create Agent
					{/if}
				</Button>
			</div>
		</div>
	</form>
</div>

<style>
	:global(.relative.flex.w-full.touch-none.select-none.items-center) {
		@apply cursor-pointer;
	}
</style>
