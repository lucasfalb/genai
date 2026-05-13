<script lang="ts">
	import { Input } from '$lib/components/ui/input/index.js';
	import { NativeSelect } from '$lib/components/ui/native-select/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import type { AgentProviderOption } from '$lib/settings/agent-ui';

	let {
		name = $bindable(),
		description = $bindable(),
		provider = $bindable(),
		model = $bindable(),
		temperature = $bindable(),
		status,
		providers
	}: {
		name: string;
		description: string;
		provider: string;
		model: string;
		temperature: number;
		status: string;
		providers: AgentProviderOption[];
	} = $props();

	const availableModels = $derived.by(() => {
		const selectedProvider = providers.find((p) => p.value === provider);
		return selectedProvider ? selectedProvider.models : [];
	});

	// Update model when provider changes if current model is not available
	$effect(() => {
		if (provider && availableModels.length > 0) {
			const modelExists = availableModels.some((m) => m.value === model);
			if (!modelExists) {
				model = availableModels[0].value;
			}
		}
	});
</script>

<div class="space-y-5 p-6" style="background:var(--surface);border:1px solid var(--ds-border)">
	<div class="flex items-center justify-between">
		<div>
			<h2 class="font-display text-sm font-semibold" style="color:var(--text-main)">Details</h2>
			<p class="mt-1 text-xs text-muted-foreground">
				Agent identity, description and runtime model.
			</p>
		</div>
		<Badge variant="outline" class="text-[10px] uppercase">{status}</Badge>
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
			<label class="block text-[11px] font-semibold tracking-widest text-muted-foreground uppercase"
				>Provider *</label
			>
			<NativeSelect bind:value={provider} class="w-full">
				{#each providers as p (p.value)}
					<option value={p.value}>{p.label}</option>
				{/each}
			</NativeSelect>
		</div>
		<div class="space-y-1.5">
			<label class="block text-[11px] font-semibold tracking-widest text-muted-foreground uppercase"
				>Model *</label
			>
			<NativeSelect bind:value={model} class="w-full">
				{#each availableModels as m (m.value)}
					<option value={m.value}>{m.label}</option>
				{/each}
			</NativeSelect>
		</div>
	</div>

	<div class="space-y-1.5">
		<label class="block text-[11px] font-semibold tracking-widest text-muted-foreground uppercase">
			Temperature — <span class="font-mono text-blue-400">{temperature.toFixed(1)}</span>
		</label>
		<input
			type="range"
			bind:value={temperature}
			min="0"
			max="2"
			step="0.1"
			class="mt-2 w-full accent-blue-500"
		/>
	</div>
</div>
