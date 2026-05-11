<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { setContext } from 'svelte';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Bot from '@lucide/svelte/icons/bot';
	import Clock from '@lucide/svelte/icons/clock';
	import FileText from '@lucide/svelte/icons/file-text';
	import HistoryIcon from '@lucide/svelte/icons/history';
	import Save from '@lucide/svelte/icons/save';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import User from '@lucide/svelte/icons/user';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import * as Sheet from '$lib/components/ui/sheet/index.js';
	import TestAgentChat from '$lib/components/instance/test-agent-chat.svelte';
	import { collectionsApi } from '$lib/api/collections';
	import { instancesApi } from '$lib/api/instances';
	import { ApiError } from '$lib/api/client';
	import { tenantBaseFromPath } from '$lib/routes/tenant';
	import { getAgentUiSettings } from '$lib/settings/agent-ui';
	import { cn } from '$lib/utils.js';

	let { data, children } = $props();

	const appBase = $derived(tenantBaseFromPath(page.url.pathname));
	const instanceBase = $derived(`${appBase}/instances/${data.instance.id}`);
	const agentUi = getAgentUiSettings(data.publicSettings);
	const evaluationSessionId = $derived(page.params.sessionId ?? null);

	let error = $state('');

	let saveHandler: (() => Promise<void>) | null = $state(null);
	let saveLabel = $state('');
	let isSaving = $state(false);

	let historyOpen = $state(false);
	let diffVersion = $state<import('$lib/api/types').VersionEntry | null>(null);
	let versions = $state<import('$lib/api/types').VersionEntry[]>([]);
	let collectionMap = $state<Record<string, string>>({});

	async function loadVersions() {
		try {
			versions = await instancesApi.getVersions(data.instance.id);
		} catch {
			versions = [];
		}
		try {
			const collections = await collectionsApi.list();
			collectionMap = Object.fromEntries(collections.map((c) => [c.id, c.name]));
		} catch {
			collectionMap = {};
		}
	}

	setContext('save-action', {
		register: (handler: () => Promise<void>, label: string) => {
			saveHandler = handler;
			saveLabel = label;
		},
		unregister: () => {
			saveHandler = null;
		},
		setSaving: (v: boolean) => {
			isSaving = v;
		}
	});

	const tabs = [
		{ href: 'overview', label: 'Overview' },
		{ href: 'instructions', label: 'Instructions' },
		{ href: 'skills', label: 'Tools' },
		{ href: 'channels', label: 'Channels' },
		{ href: 'debug', label: 'Debug' },
		{ href: 'evaluations', label: 'Evaluations' }
	];

	function isActive(href: string) {
		return page.url.pathname.endsWith(`/${href}`) || page.url.pathname.includes(`/${href}/`);
	}

	function escapeHtml(s: string): string {
		return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
	}

	function formatValue(key: string, value: unknown): string {
		if (value === null || value === undefined)
			return '<span class="italic text-muted-foreground">not set</span>';
		if (key === 'temperature') return Number(value).toFixed(1);
		if (key === 'rag_scope') {
			const arr = Array.isArray(value) ? value : [];
			if (arr.length === 0)
				return '<span class="italic text-muted-foreground">all collections</span>';
			return arr
				.map((id: string) => {
					const name = collectionMap[id];
					return `<span class="inline-block rounded-sm px-1.5 py-0.5 text-[10px]" style="background:var(--surface);border:1px solid var(--ds-border)">${name ? escapeHtml(name) : `<span class="italic text-muted-foreground">deleted (${id.slice(0, 8)})</span>`}</span>`;
				})
				.join(' ');
		}
		if (key === 'core_prompt') {
			const s = String(value);
			return s.length > 200 ? s.slice(0, 200) + '...' : s;
		}
		if (key === 'status') return `<span class="capitalize">${value}</span>`;
		return String(value);
	}

	async function deleteInstance() {
		if (!confirm(`Delete "${data.instance.name}"? This cannot be undone.`)) return;
		try {
			await instancesApi.delete(data.instance.id);
			await goto(`${appBase}/instances`);
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Delete failed.';
		}
	}
</script>

<div class="flex h-full flex-col overflow-hidden">
	{#if error}
		<div class="px-5 pt-3">
			<div
				class="rounded-xl px-4 py-3 text-sm text-red-400"
				style="background:color-mix(in srgb,red 8%,transparent);border:1px solid color-mix(in srgb,red 18%,transparent)"
			>
				{error}
			</div>
		</div>
	{/if}

	<!-- Header -->
	<header
		class="flex h-[49px] shrink-0 items-center justify-between gap-4 border-b bg-[var(--surface)] px-2"
		style="border-color:var(--ds-border)"
	>
		<div class="flex min-w-0 items-center gap-3">
			<a
				href="{appBase}/instances"
				class="rounded-md p-1.5 transition-colors hover:bg-[var(--surface-hover)]"
				aria-label="Back to agents"
			>
				<ArrowLeft class="h-4 w-4 text-muted-foreground" />
			</a>
			<div
				class="flex size-8 shrink-0 items-center justify-center rounded-full border bg-blue-500/10 text-blue-500"
				style="border-color:color-mix(in srgb, var(--ds-border) 70%, #3b82f6 30%)"
			>
				<Bot class="size-4" />
			</div>
			<div class="min-w-0">
				<div class="flex items-center gap-2">
					<h1 class="truncate text-sm font-semibold" style="color:var(--text-main)">
						{data.instance.name}
					</h1>
				</div>
			</div>
		</div>
		<div class="flex shrink-0 items-center gap-2">
			{#if saveHandler}
				<Button onclick={saveHandler} disabled={isSaving}>
					{#if isSaving}<Spinner data-icon="inline-start" />{:else}<Save
							data-icon="inline-start"
						/>{/if}
					{saveLabel}
				</Button>
			{/if}
			<Button
				variant="outline"
				onclick={() => {
					loadVersions();
					historyOpen = true;
				}}
			>
				<HistoryIcon class="size-3.5" />
				History
			</Button>
			<button
				onclick={deleteInstance}
				class="rounded-md p-1.5 text-red-400 transition-colors hover:bg-red-400/10"
				aria-label="Delete agent"
			>
				<Trash2 class="h-4 w-4" />
			</button>
		</div>
	</header>

	<!-- Tab nav -->
	<nav
		class="flex h-11 shrink-0 items-center gap-5 border-b bg-[var(--surface)] px-6 text-xs"
		style="border-color:var(--ds-border)"
	>
		{#each tabs as tab (tab.href)}
			{@const active = isActive(tab.href)}
			<a
				href="{instanceBase}/{tab.href}"
				class={cn(
					'relative inline-flex h-full items-center font-semibold transition-colors',
					active ? 'text-blue-500' : 'text-muted-foreground hover:text-foreground'
				)}
			>
				{tab.label}
				{#if active}
					<span class="absolute inset-x-0 bottom-0 h-0.5 rounded-full bg-blue-500"></span>
				{/if}
			</a>
		{/each}
	</nav>

	<!-- Resizable split: 65 main / 35 chat -->
	<Resizable.PaneGroup direction="horizontal" class="flex-1 overflow-hidden">
		<Resizable.Pane defaultSize={65} minSize={30}>
			<div class="h-full overflow-y-auto">
				{@render children()}
			</div>
		</Resizable.Pane>
		<Resizable.Handle withHandle />
		{#if agentUi.test_panel_enabled}
			<Resizable.Pane defaultSize={35} minSize={20}>
			<TestAgentChat
				instanceId={data.instance.id}
				instanceName={data.instance.name}
				collectionsHref={`${appBase}/collections`}
				sessionId={evaluationSessionId}
			/>
			</Resizable.Pane>
		{/if}
	</Resizable.PaneGroup>
</div>

<Sheet.Root bind:open={historyOpen}>
	<Sheet.Content side="right" class="w-80 sm:max-w-sm">
		<Sheet.Header>
			<Sheet.Title class="flex items-center gap-2">
				<Clock class="size-4" />
				Version History
			</Sheet.Title>
			<Sheet.Description>Saved versions of this agent instance.</Sheet.Description>
		</Sheet.Header>
		<div class="flex-1 overflow-y-auto px-4 py-2">
			{#if versions.length === 0}
				<p class="py-8 text-center text-xs text-muted-foreground">No versions yet.</p>
			{:else}
				<div class="space-y-1">
					{#each versions as v (v.version)}
						<button
							onclick={() => {
								diffVersion = v;
							}}
							class="flex w-full items-start gap-3 rounded-md px-3 py-2.5 text-left transition-colors hover:bg-[var(--surface-hover)]"
						>
							<div
								class={`flex size-7 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${v.action.includes('updated') ? 'bg-blue-500/10 text-blue-500' : ''} ${v.action.includes('created') ? 'bg-green-500/10 text-green-500' : ''}`}
							>
								{v.version}
							</div>
							<div class="min-w-0 flex-1">
								<div class="flex items-center justify-between gap-2">
									<span class="truncate text-xs font-medium">
										{v.action === 'agent_instance.created' ? 'Created' : 'Saved'}
									</span>
									<span class="shrink-0 text-[10px] text-muted-foreground">
										{v.created_at ? new Date(v.created_at).toLocaleString('pt-BR') : '-'}
									</span>
								</div>
								<p class="mt-0.5 truncate text-[10px] text-muted-foreground">
									<User class="mr-1 inline size-3" />
									{v.changed_by}
								</p>
							</div>
						</button>
						{#if v !== versions[versions.length - 1]}
							<div
								class="ml-[22px] border-l"
								style="border-color:var(--ds-border);height:8px"
							></div>
						{/if}
					{/each}
				</div>
			{/if}
		</div>
	</Sheet.Content>
</Sheet.Root>

<Dialog.Root
	open={diffVersion !== null}
	onOpenChange={(o) => {
		if (!o) diffVersion = null;
	}}
>
	<Dialog.Content class="max-w-3xl">
		<Dialog.Header>
			<Dialog.Title class="flex items-center gap-2">
				<FileText class="size-4" />
				Version {diffVersion?.version} — {diffVersion?.action === 'agent_instance.created'
					? 'Created'
					: 'Saved'}
			</Dialog.Title>
			<Dialog.Description>
				{diffVersion?.changed_by ?? 'Unknown'} — {diffVersion?.created_at
					? new Date(diffVersion.created_at).toLocaleString('pt-BR')
					: ''}
			</Dialog.Description>
		</Dialog.Header>
		{#if diffVersion}
			{@const internalFields = new Set(['id', 'tenant_id', 'created_by'])}
			{@const fieldLabels: Record<string, string> = {
				name: 'Name', description: 'Description', core_prompt: 'Core Prompt',
				model: 'Model', temperature: 'Temperature', status: 'Status', rag_scope: 'Knowledge Scope'
			}}
			{@const compareFields = Object.keys(diffVersion.snapshot).filter(
				(k) => !internalFields.has(k)
			)}
			{@const hasChanges = compareFields.some((k) => {
				const oldVal = diffVersion!.snapshot[k];
				const curVal = data.instance[k as keyof typeof data.instance];
				return JSON.stringify(oldVal) !== JSON.stringify(curVal);
			})}
			<div class="max-h-[28rem] overflow-y-auto px-4 py-2">
				{#if !hasChanges}
					<div class="flex items-center gap-2 rounded-md bg-green-500/5 p-3 text-xs text-green-400">
						No differences — this version matches the current state.
					</div>
				{/if}
				<div class="space-y-1">
					{#each compareFields as key}
						{@const oldVal = diffVersion.snapshot[key]}
						{@const curVal = data.instance[key as keyof typeof data.instance]}
						{@const changed = JSON.stringify(oldVal) !== JSON.stringify(curVal)}
						{@const label = fieldLabels[key] ?? key}
						{#if changed}
							<div class="overflow-hidden rounded-md border border-amber-500/30">
								<div
									class="flex items-center justify-between gap-2 bg-amber-500/5 px-3 py-1.5 text-[10px] font-semibold tracking-wider uppercase"
								>
									<span>{label}</span>
									<span
										class="inline-flex items-center gap-1 rounded-sm bg-amber-500/10 px-1.5 py-0.5 text-[9px] text-amber-400"
										>Modified</span
									>
								</div>
								<div class="grid grid-cols-2 divide-x" style="border-color:var(--ds-border)">
									<div class="bg-red-500/[0.03] p-3 font-mono text-xs leading-relaxed">
										<span class="mb-1.5 block text-[9px] font-semibold tracking-wider text-red-400"
											>Version {diffVersion.version}</span
										>
										<div class="line-through decoration-red-400/40">
											{@html formatValue(key, oldVal)}
										</div>
									</div>
									<div class="bg-green-500/[0.03] p-3 font-mono text-xs leading-relaxed">
										<span
											class="mb-1.5 block text-[9px] font-semibold tracking-wider text-green-400"
											>Current</span
										>
										{@html formatValue(key, curVal)}
									</div>
								</div>
							</div>
						{:else}
							<div
								class="flex items-center justify-between gap-2 rounded-md px-3 py-2 text-xs"
								style="background:var(--surface)"
							>
								<span
									class="text-[10px] font-semibold tracking-wider uppercase"
									style="color:var(--text-muted)">{label}</span
								>
								<span class="text-right font-mono">{@html formatValue(key, curVal)}</span>
							</div>
						{/if}
					{/each}
				</div>
			</div>
		{/if}
	</Dialog.Content>
</Dialog.Root>
