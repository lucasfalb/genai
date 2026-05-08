<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Command from '$lib/components/ui/command/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { registryApi } from '$lib/api/registry';
	import { getErrorMessage } from '$lib/api/client';
	import { toast } from 'svelte-sonner';
	import type { CatalogSkillResponse, CatalogToolResponse } from '$lib/api/types';
	import Cpu from '@lucide/svelte/icons/cpu';
	import Wrench from '@lucide/svelte/icons/wrench';
	import KeyRound from '@lucide/svelte/icons/key-round';

	let {
		open = $bindable(false),
		kind,
		excludeSlugs,
		onPick
	}: {
		open: boolean;
		kind: 'skill' | 'tool';
		excludeSlugs: string[];
		onPick: (slug: string) => Promise<void>;
	} = $props();

	let loading = $state(false);
	let skills = $state<CatalogSkillResponse[]>([]);
	let tools = $state<CatalogToolResponse[]>([]);
	let picking = $state('');

	$effect(() => {
		if (open) loadCatalog();
	});

	async function loadCatalog() {
		loading = true;
		try {
			const catalog = await registryApi.getCatalog();
			skills = catalog.skills;
			tools = catalog.tools;
		} catch (err) {
			toast.error(getErrorMessage(err, 'Failed to load catalog.'));
		} finally {
			loading = false;
		}
	}

	const items = $derived(
		kind === 'skill'
			? skills.filter((s) => !excludeSlugs.includes(s.slug))
			: tools.filter((t) => !excludeSlugs.includes(t.slug))
	);

	async function pick(slug: string) {
		picking = slug;
		try {
			await onPick(slug);
			open = false;
		} finally {
			picking = '';
		}
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-lg">
		<Dialog.Header>
			<Dialog.Title>Add {kind === 'skill' ? 'Skill' : 'Tool'}</Dialog.Title>
			<Dialog.Description>
				{kind === 'skill'
					? 'Pick a skill from the global catalog to activate on this agent.'
					: 'Pick a utility tool from the catalog.'}
			</Dialog.Description>
		</Dialog.Header>

		{#if loading}
			<div class="flex items-center justify-center py-12">
				<Spinner />
			</div>
		{:else if items.length === 0}
			<p class="py-12 text-center text-sm text-muted-foreground">
				No {kind}s available in the catalog.
			</p>
		{:else}
			<Command.Root>
				<Command.Input placeholder="Search {kind}s..." />
				<Command.List>
					<Command.Empty>No matches.</Command.Empty>
					<Command.Group heading={kind === 'skill' ? 'Skills' : 'Tools'}>
						{#each items as item (item.slug)}
							<Command.Item value={item.slug} onSelect={() => pick(item.slug)}>
								<div class="flex size-8 shrink-0 items-center justify-center rounded-md bg-blue-500/10 text-blue-400">
									{#if kind === 'skill'}<Cpu class="size-4" />{:else}<Wrench class="size-4" />{/if}
								</div>
								<div class="min-w-0 flex-1">
									<div class="flex items-center gap-2">
										<p class="font-mono text-xs font-semibold">{item.slug}</p>
										{#if item.category}<Badge variant="outline" class="text-[10px]">{item.category}</Badge>{/if}
										{#if kind === 'skill' && (item as CatalogSkillResponse).requires_credential}
											<Badge variant="outline" class="text-[10px]"><KeyRound class="size-3 mr-1" />cred</Badge>
										{/if}
									</div>
									<p class="truncate text-xs text-muted-foreground">{item.name}</p>
									{#if item.description}<p class="line-clamp-1 text-xs text-muted-foreground/70">{item.description}</p>{/if}
								</div>
								{#if picking === item.slug}<Spinner />{/if}
							</Command.Item>
						{/each}
					</Command.Group>
				</Command.List>
			</Command.Root>
		{/if}

		<Dialog.Footer>
			<Button variant="ghost" onclick={() => (open = false)}>Cancel</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
