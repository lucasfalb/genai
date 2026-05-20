<script lang="ts">
	import Search from '@lucide/svelte/icons/search';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import FilterCombobox from './filter-combobox.svelte';

	type Option = { value: string; label: string };

	let {
		open = $bindable(false),
		searchTerm = $bindable(''),
		agentFilter = $bindable('all'),
		channelFilter = $bindable('all'),
		osFilter = $bindable('all'),
		browserFilter = $bindable('all'),
		cityFilter = $bindable('all'),
		agentOptions,
		channelOptions,
		osOptions,
		browserOptions,
		cityOptions,
		hasActiveFilters,
		clearFilters
	}: {
		open: boolean;
		searchTerm: string;
		agentFilter: string;
		channelFilter: string;
		osFilter: string;
		browserFilter: string;
		cityFilter: string;
		agentOptions: Option[];
		channelOptions: Option[];
		osOptions: string[];
		browserOptions: string[];
		cityOptions: string[];
		hasActiveFilters: boolean;
		clearFilters: () => void;
	} = $props();

	const osFilterOptions = $derived([
		{ value: 'all', label: 'All systems' },
		...osOptions.map((option) => ({ value: option, label: option }))
	]);
	const browserFilterOptions = $derived([
		{ value: 'all', label: 'All browsers' },
		...browserOptions.map((option) => ({ value: option, label: option }))
	]);
	const cityFilterOptions = $derived([
		{ value: 'all', label: 'All cities' },
		...cityOptions.map((option) => ({ value: option, label: option }))
	]);
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="max-h-[86vh] overflow-y-auto sm:max-w-xl">
		<Dialog.Header>
			<Dialog.Title>Advanced filters</Dialog.Title>
			<Dialog.Description>
				Refine conversations by channel, agent, device, browser, or location.
			</Dialog.Description>
		</Dialog.Header>

		<div class="grid gap-4 py-1 sm:grid-cols-2">
			<div class="space-y-1.5 sm:col-span-2">
				<div class="text-[11px] font-semibold tracking-widest text-muted-foreground uppercase">
					Search
				</div>
				<div class="relative">
					<Search class="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
					<Input
						class="h-9 pl-9"
						placeholder="Session, visitor, city, browser..."
						bind:value={searchTerm}
					/>
				</div>
			</div>

			<FilterCombobox
				label="Agent"
				bind:value={agentFilter}
				options={agentOptions}
				placeholder="Search agents..."
			/>
			<FilterCombobox
				label="Channel"
				bind:value={channelFilter}
				options={channelOptions}
				placeholder="Search channels..."
			/>
			<FilterCombobox
				label="Operating system"
				bind:value={osFilter}
				options={osFilterOptions}
				placeholder="Search systems..."
			/>
			<FilterCombobox
				label="Browser"
				bind:value={browserFilter}
				options={browserFilterOptions}
				placeholder="Search browsers..."
			/>
			<FilterCombobox
				label="City"
				class="sm:col-span-2"
				bind:value={cityFilter}
				options={cityFilterOptions}
				placeholder="Search cities..."
			/>
		</div>

		<Dialog.Footer class="gap-2 sm:justify-between">
			<Button variant="ghost" onclick={clearFilters} disabled={!hasActiveFilters}>Clear filters</Button>
			<Button onclick={() => (open = false)}>Apply filters</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
