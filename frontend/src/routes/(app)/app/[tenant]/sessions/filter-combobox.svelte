<script lang="ts">
	import Check from '@lucide/svelte/icons/check';
	import ChevronsUpDown from '@lucide/svelte/icons/chevrons-up-down';
	import * as Command from '$lib/components/ui/command/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';

	type Option = { value: string; label: string };

	let {
		label,
		value = $bindable('all'),
		options,
		placeholder = 'Search...',
		empty = 'No matches.',
		class: className = ''
	}: {
		label: string;
		value: string;
		options: Option[];
		placeholder?: string;
		empty?: string;
		class?: string;
	} = $props();

	let open = $state(false);
	const listId = $derived(`filter-combobox-${label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`);
	const selectedLabel = $derived(options.find((option) => option.value === value)?.label ?? label);
</script>

<div class={`space-y-1.5 ${className}`}>
	<div class="text-[11px] font-semibold tracking-widest text-muted-foreground uppercase">{label}</div>
	<Popover.Root bind:open>
		<Popover.Trigger class="w-full">
			<button
				type="button"
				role="combobox"
				aria-expanded={open}
				aria-controls={listId}
				aria-haspopup="listbox"
				class="flex h-9 w-full min-w-0 items-center justify-between border bg-background px-3 py-2 text-sm"
				style="border-color:var(--ds-border)"
			>
				<span class="truncate">{selectedLabel}</span>
				<ChevronsUpDown class="ml-2 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
			</button>
		</Popover.Trigger>
		<Popover.Content class="w-[--bits-popover-anchor-width] min-w-56 p-0">
			<Command.Root>
				<Command.Input {placeholder} class="h-9" />
				<Command.List id={listId} class="max-h-60 overflow-y-auto">
					<Command.Empty>{empty}</Command.Empty>
					<Command.Group>
						{#each options as option (option.value)}
							<Command.Item
								value={`${option.label} ${option.value}`}
								onSelect={() => {
									value = option.value;
									open = false;
								}}
							>
								<Check
									class={[
										'mr-2 h-3.5 w-3.5 shrink-0',
										value === option.value ? 'opacity-100' : 'opacity-0'
									]}
								/>
								<span class="truncate">{option.label}</span>
							</Command.Item>
						{/each}
					</Command.Group>
				</Command.List>
			</Command.Root>
		</Popover.Content>
	</Popover.Root>
</div>
