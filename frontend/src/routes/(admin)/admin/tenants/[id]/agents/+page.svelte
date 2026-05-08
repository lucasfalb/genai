<script lang="ts">
	import type { SuperadminAgentInstanceResponse } from '$lib/api/types';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import * as Empty from '$lib/components/ui/empty/index.js';
	import Network from '@lucide/svelte/icons/network';

	let { data } = $props();
	const instances = data.instances as SuperadminAgentInstanceResponse[];

	function statusVariant(s: string): 'default' | 'outline' | 'secondary' {
		if (s === 'active') return 'default';
		if (s === 'archived') return 'outline';
		return 'secondary';
	}
</script>

<div class="flex flex-col gap-4 p-6">
	<div class="flex items-center gap-2">
		<Network class="size-4 text-muted-foreground" />
		<span class="text-sm font-semibold">Agent Instances</span>
		<Badge variant="secondary">{instances.length}</Badge>
	</div>

	<div class="rounded-lg border">
		{#if instances.length === 0}
			<Empty.Root>
				<Empty.Title>No instances</Empty.Title>
				<Empty.Description>This tenant has no agent instances yet.</Empty.Description>
			</Empty.Root>
		{:else}
			<Table.Root>
				<Table.Header>
					<Table.Row>
						<Table.Head>Name</Table.Head>
						<Table.Head>Model</Table.Head>
						<Table.Head>Status</Table.Head>
						<Table.Head>Description</Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body>
					{#each instances as inst (inst.id)}
						<Table.Row>
							<Table.Cell class="text-sm font-medium">{inst.name}</Table.Cell>
							<Table.Cell>
								<Badge variant="outline" class="font-mono text-xs">{inst.model}</Badge>
							</Table.Cell>
							<Table.Cell>
								<Badge variant={statusVariant(inst.status)}>{inst.status}</Badge>
							</Table.Cell>
							<Table.Cell class="text-xs text-muted-foreground">{inst.description ?? '—'}</Table.Cell>
						</Table.Row>
					{/each}
				</Table.Body>
			</Table.Root>
		{/if}
	</div>
</div>
