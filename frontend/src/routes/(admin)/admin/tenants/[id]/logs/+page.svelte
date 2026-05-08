<script lang="ts">
	import type { SuperadminAuditLogResponse } from '$lib/api/types';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import * as Empty from '$lib/components/ui/empty/index.js';
	import Activity from '@lucide/svelte/icons/activity';

	let { data } = $props();
	const logs = data.logs as SuperadminAuditLogResponse[];

	function formatDate(iso: string): string {
		return new Date(iso).toLocaleString();
	}
</script>

<div class="flex flex-col gap-4 p-6">
	<div class="flex items-center gap-2">
		<Activity class="size-4 text-muted-foreground" />
		<span class="text-sm font-semibold">Audit Logs</span>
		<Badge variant="secondary">{logs.length} recent</Badge>
	</div>

	<div class="rounded-lg border">
		{#if logs.length === 0}
			<Empty.Root>
				<Empty.Title>No audit logs</Empty.Title>
				<Empty.Description>No activity has been recorded for this tenant yet.</Empty.Description>
			</Empty.Root>
		{:else}
			<Table.Root>
				<Table.Header>
					<Table.Row>
						<Table.Head>When</Table.Head>
						<Table.Head>Action</Table.Head>
						<Table.Head>Resource</Table.Head>
						<Table.Head>Resource ID</Table.Head>
						<Table.Head>Actor</Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body>
					{#each logs as log (log.id)}
						<Table.Row>
							<Table.Cell class="whitespace-nowrap font-mono text-xs text-muted-foreground">
								{formatDate(log.created_at)}
							</Table.Cell>
							<Table.Cell class="font-mono text-xs font-medium">{log.action}</Table.Cell>
							<Table.Cell class="text-xs text-muted-foreground">{log.resource}</Table.Cell>
							<Table.Cell class="max-w-32 truncate font-mono text-xs text-muted-foreground">
								{log.resource_id ?? '—'}
							</Table.Cell>
							<Table.Cell class="text-xs text-muted-foreground">{log.actor_type}</Table.Cell>
						</Table.Row>
					{/each}
				</Table.Body>
			</Table.Root>
		{/if}
	</div>
</div>
