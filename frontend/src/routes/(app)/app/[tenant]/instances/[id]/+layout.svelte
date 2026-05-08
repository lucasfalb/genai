<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Bot from '@lucide/svelte/icons/bot';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Database from '@lucide/svelte/icons/database';
	import MoreHorizontal from '@lucide/svelte/icons/more-horizontal';
	import Send from '@lucide/svelte/icons/send';
	import SettingsIcon from '@lucide/svelte/icons/settings';
	import ThumbsDown from '@lucide/svelte/icons/thumbs-down';
	import ThumbsUp from '@lucide/svelte/icons/thumbs-up';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import { instancesApi } from '$lib/api/instances';
	import { ApiError } from '$lib/api/client';
	import { tenantBaseFromPath } from '$lib/routes/tenant';
	import { getAgentUiSettings } from '$lib/settings/agent-ui';
	import { cn } from '$lib/utils.js';

	let { data, children } = $props();

	const appBase = $derived(tenantBaseFromPath(page.url.pathname));
	const instanceBase = $derived(`${appBase}/instances/${data.instance.id}`);
	const agentUi = getAgentUiSettings(data.publicSettings);

	let error = $state('');
	let testMessage = $state('');

	const tabs = [
		{ href: 'overview', label: 'Overview' },
		{ href: 'instructions', label: 'Instructions' },
		{ href: 'skills', label: 'Tools' },
		{ href: 'channels', label: 'Channels' }
	];

	function isActive(href: string) {
		return page.url.pathname.endsWith(`/${href}`) || page.url.pathname.includes(`/${href}/`);
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
		class="flex h-14 shrink-0 items-center justify-between gap-4 border-b bg-[var(--surface)] px-5"
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
			<button
				class="rounded-md border px-3 py-1.5 text-xs font-semibold transition-colors hover:bg-[var(--surface-hover)]"
				style="border-color:var(--ds-border)">Publish</button
			>
			<button
				class="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-semibold transition-colors hover:bg-[var(--surface-hover)]"
				style="border-color:var(--ds-border)"
			>
				<SettingsIcon class="size-3.5" />
				Settings
			</button>
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
				<aside class="flex h-full flex-col overflow-hidden bg-[var(--surface)]">
					<!-- Aside header -->
					<div
						class="flex h-14 shrink-0 items-center justify-between border-b px-5"
						style="border-color:var(--ds-border)"
					>
						<div class="flex items-center gap-2">
							<Bot class="size-4 text-muted-foreground" />
							<h2 class="text-sm font-semibold" style="color:var(--text-main)">Test agent</h2>
						</div>
						<div class="flex items-center gap-1">
							<a
								href="{appBase}/collections"
								class="rounded p-1.5 text-muted-foreground transition-colors hover:bg-[var(--surface-hover)] hover:text-foreground"
								title="Collections & Knowledge"
							>
								<Database class="size-4" />
							</a>
							<button
								class="rounded p-1.5 text-muted-foreground transition-colors hover:bg-[var(--surface-hover)] hover:text-foreground"
								aria-label="More actions"
							>
								<MoreHorizontal class="size-4" />
							</button>
						</div>
					</div>

					<!-- Chat messages area -->
					<div class="flex flex-1 flex-col justify-end gap-4 overflow-y-auto p-4">
						<div
							class="rounded-xl border bg-[var(--canvas)] p-4"
							style="border-color:var(--ds-border)"
						>
							<div class="flex items-start gap-3">
								<div
									class="flex size-8 shrink-0 items-center justify-center rounded-full bg-blue-500/10 text-blue-500"
								>
									<Bot class="size-4" />
								</div>
								<div class="min-w-0 text-sm leading-relaxed">
									<p class="font-semibold" style="color:var(--text-main)">
										{data.instance.name} pronto.
									</p>
									<p class="mt-1 text-muted-foreground">
										Use este painel para validar instrucoes, guardrails e conhecimento antes de
										publicar.
									</p>
									<ol class="mt-3 list-decimal space-y-1 pl-4 text-xs text-muted-foreground">
										<li>Teste perguntas comuns do tenant.</li>
										<li>Valide respostas com documentos e colecoes.</li>
										<li>Confirme limites definidos nos guardrails.</li>
									</ol>
									<p class="mt-3 text-xs font-semibold" style="color:var(--text-main)">
										O que voce gostaria de investigar primeiro?
									</p>
									<div class="mt-3 flex gap-2 text-muted-foreground">
										<ThumbsUp class="size-4" />
										<ThumbsDown class="size-4" />
									</div>
								</div>
							</div>
						</div>
					</div>

					<!-- Message input -->
					<div class="shrink-0 border-t p-4" style="border-color:var(--ds-border)">
						<div
							class="rounded-xl border bg-[var(--canvas)] p-3 shadow-sm"
							style="border-color:var(--ds-border)"
						>
							<textarea
								bind:value={testMessage}
								rows="3"
								maxlength="2000"
								placeholder="Faca uma pergunta ou descreva o que precisa"
								class="w-full resize-none bg-transparent text-sm outline-none placeholder:text-muted-foreground"
							></textarea>
							<div class="mt-2 flex items-center justify-between">
								<span class="font-mono text-[10px] text-muted-foreground"
									>{testMessage.length}/2000</span
								>
								<button
									type="button"
									disabled={!testMessage.trim()}
									class="inline-flex size-8 items-center justify-center rounded-md bg-blue-600 text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40"
									aria-label="Send test message"
								>
									<Send class="size-4" />
								</button>
							</div>
						</div>
					</div>
				</aside>
			</Resizable.Pane>
		{/if}
	</Resizable.PaneGroup>
</div>
