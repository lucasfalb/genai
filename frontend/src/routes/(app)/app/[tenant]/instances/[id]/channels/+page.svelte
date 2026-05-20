<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import ChannelCard from '$lib/components/instance/channel-card.svelte';
	import ChannelConfigWeb from '$lib/components/instance/channel-config-web.svelte';
	import ChannelConfigApi from '$lib/components/instance/channel-config-api.svelte';
	import Globe from '@lucide/svelte/icons/globe';
	import Code from '@lucide/svelte/icons/code';
	import Eye from '@lucide/svelte/icons/eye';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import { toast } from 'svelte-sonner';
	import { instancesApi } from '$lib/api/instances';
	import type { WebWidgetConfig } from '$lib/api/types';
	import { defaultWebWidgetConfig } from '$lib/api/types';
	import { Button } from '$lib/components/ui/button/index.js';

	let { data } = $props();

	const { register, unregister, setSaving } = getContext<{
		register: (handler: () => Promise<void>, label: string) => void;
		unregister: () => void;
		setSaving: (v: boolean) => void;
	}>('save-action');

	const rightPanel = getContext<{
		setWidgetPreview: (cfg: WebWidgetConfig) => void;
		updateWidgetConfig: (cfg: WebWidgetConfig) => void;
		resetToChat: () => void;
	}>('right-panel');

	let webEnabled = $state(false);
	let apiEnabled = $state(false);

	let widgetConfig = $state<WebWidgetConfig>(defaultWebWidgetConfig());
	let widgetDomains = $state('');
	let loading = $state(true);
	let previewActive = $state(false);

	$effect(() => {
		if (previewActive) {
			rightPanel?.updateWidgetConfig(widgetConfig);
		}
	});

	onMount(() => {
		instancesApi.getChannelConfig(data.instance.id, 'widget').then((res) => {
			webEnabled = res.is_active;
			if (res.config && Object.keys(res.config).length > 0) {
				widgetConfig = { ...defaultWebWidgetConfig(), ...res.config } as WebWidgetConfig;
			}
			widgetDomains = (res.allowed_origins ?? []).join('\n');
		}).catch(() => {
			// no existing config — use defaults
		}).finally(() => {
			loading = false;
		});

		register(saveChannels, 'Save changes');
		return () => {
			unregister();
			rightPanel?.resetToChat();
		};
	});

	function togglePreview() {
		previewActive = !previewActive;
		if (previewActive) {
			rightPanel?.setWidgetPreview(widgetConfig);
		} else {
			rightPanel?.resetToChat();
		}
	}

	async function toggleWeb(enabled: boolean) {
		webEnabled = enabled;
		try {
			if (enabled) {
				await instancesApi.activateChannel(data.instance.id, 'widget');
			} else {
				await instancesApi.deactivateChannel(data.instance.id, 'widget');
			}
		} catch {
			toast.error('Failed to update channel status.');
			webEnabled = !enabled;
		}
	}

	async function saveChannels() {
		setSaving(true);
		try {
			const origins = widgetDomains
				.split(/[\n,]+/)
				.map((d) => d.trim())
				.filter(Boolean);

			await instancesApi.updateChannelConfig(data.instance.id, 'widget', {
				config: widgetConfig,
				allowed_origins: origins,
				is_active: webEnabled,
			});
			toast.success('Channel settings saved.');
		} catch {
			toast.error('Failed to save channel settings.');
		} finally {
			setSaving(false);
		}
	}
</script>

<div class="mx-auto max-w-4xl space-y-5 px-6 py-5">
	<div class="flex items-start justify-between gap-4">
		<div>
			<h2 class="font-display text-base font-semibold" style="color:var(--text-main)">Channels</h2>
			<p class="mt-1 text-xs text-muted-foreground">
				Where this agent is available. Enable a channel to expand its setup.
			</p>
		</div>
		{#if !loading}
			<Button
				variant={previewActive ? 'default' : 'outline'}
				size="sm"
				onclick={togglePreview}
				class="shrink-0"
			>
				{#if previewActive}
					<EyeOff class="mr-1.5 size-3.5" />
					Exit preview
				{:else}
					<Eye class="mr-1.5 size-3.5" />
					Preview widget
				{/if}
			</Button>
		{/if}
	</div>

	<section class="space-y-2">
		<p class="text-[11px] font-semibold tracking-widest text-muted-foreground uppercase">
			Web & API
		</p>
		<div class="space-y-3">
			<ChannelCard
				icon={Globe}
				name="Web Widget"
				description="Embed a chat widget on your website with a single script tag."
				enabled={webEnabled}
				ontoggle={toggleWeb}
			>
				{#snippet children()}
					{#if !loading}
						<ChannelConfigWeb
							instanceId={data.instance.id}
							tenantId={data.instance.tenant_id}
							config={widgetConfig}
							allowedDomains={widgetDomains}
							onchange={(cfg, domains) => {
								widgetConfig = cfg;
								widgetDomains = domains;
							}}
						/>
					{/if}
				{/snippet}
			</ChannelCard>
			<ChannelCard
				icon={Code}
				name="REST API"
				description="Programmatic chat via /agent/instances/{'{'}id{'}'}/chat with bearer auth."
				bind:enabled={apiEnabled}
			>
				{#snippet children()}
					<ChannelConfigApi instanceId={data.instance.id} />
				{/snippet}
			</ChannelCard>
		</div>
	</section>
</div>
