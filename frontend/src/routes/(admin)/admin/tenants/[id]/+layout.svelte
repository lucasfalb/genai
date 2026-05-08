<script lang="ts">
	import { page } from '$app/state';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { cn } from '$lib/utils.js';
	import * as Breadcrumb from '$lib/components/ui/breadcrumb/index.js';
	import Building2 from '@lucide/svelte/icons/building-2';

	let { data, children } = $props();

	const tabs = [
		{ href: 'members', label: 'Members' },
		{ href: 'agents', label: 'Agents' },
		{ href: 'logs', label: 'Audit Logs' }
	];

	function planVariant(plan: string): 'default' | 'secondary' | 'outline' {
		if (plan === 'enterprise') return 'default';
		if (plan === 'pro') return 'secondary';
		return 'outline';
	}

	const base = $derived(`/admin/tenants/${data.tenant.id}`);
	const currentPath = $derived(page.url.pathname);
</script>

<div class="flex flex-col gap-0">
	<!-- Breadcrumb + tenant header -->
	<div class="flex flex-col gap-3 border-b bg-card px-6 py-4">
		<Breadcrumb.Root>
			<Breadcrumb.List>
				<Breadcrumb.Item>
					<Breadcrumb.Link href="/admin/tenants">Tenants</Breadcrumb.Link>
				</Breadcrumb.Item>
				<Breadcrumb.Separator />
				<Breadcrumb.Item>
					<Breadcrumb.Page>{data.tenant.name}</Breadcrumb.Page>
				</Breadcrumb.Item>
			</Breadcrumb.List>
		</Breadcrumb.Root>

		<div class="flex items-center gap-3">
			<div class="flex size-8 items-center justify-center rounded-lg bg-blue-500/10">
				<Building2 class="size-4 text-blue-400" />
			</div>
			<div class="flex flex-1 items-center gap-2">
				<h1 class="text-sm font-semibold">{data.tenant.name}</h1>
				<span class="font-mono text-xs text-muted-foreground">{data.tenant.slug}</span>
				<Badge variant={planVariant(data.tenant.plan)}>{data.tenant.plan}</Badge>
				<StatusBadge status={data.tenant.status} />
			</div>
		</div>

		<!-- Route-based tab navigation -->
		<div class="flex gap-1">
			{#each tabs as tab}
				{@const href = `${base}/${tab.href}`}
				{@const active = currentPath.startsWith(href)}
				<a
					{href}
					class={cn(
						'rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
						active
							? 'bg-primary text-primary-foreground'
							: 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
					)}
				>
					{tab.label}
				</a>
			{/each}
		</div>
	</div>

	{@render children()}
</div>
