<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import ChannelCard from '$lib/components/instance/channel-card.svelte';
	import ChannelConfigWeb from '$lib/components/instance/channel-config-web.svelte';
	import ChannelConfigApi from '$lib/components/instance/channel-config-api.svelte';
	import Globe from '@lucide/svelte/icons/globe';
	import Code from '@lucide/svelte/icons/code';
	import MessageSquare from '@lucide/svelte/icons/message-square';
	import Mail from '@lucide/svelte/icons/mail';
	import Phone from '@lucide/svelte/icons/phone';
	import Hash from '@lucide/svelte/icons/hash';
	import Send from '@lucide/svelte/icons/send';
	import Webhook from '@lucide/svelte/icons/webhook';
	import { toast } from 'svelte-sonner';

	let { data } = $props();

	const { register, unregister, setSaving } = getContext<{
		register: (handler: () => Promise<void>, label: string) => void;
		unregister: () => void;
		setSaving: (v: boolean) => void;
	}>('save-action');

	let webEnabled = $state(false);
	let apiEnabled = $state(false);

	async function saveChannels() {
		setSaving(true);
		try {
			toast.success('Channel settings saved.');
		} finally {
			setSaving(false);
		}
	}

	onMount(() => {
		register(saveChannels, 'Save changes');
		return () => unregister();
	});
</script>

<div class="mx-auto max-w-4xl space-y-5 px-6 py-5">
	<div>
		<h2 class="font-display text-base font-semibold" style="color:var(--text-main)">Channels</h2>
		<p class="mt-1 text-xs text-muted-foreground">Where this agent is available. Enable a channel to expand its setup.</p>
	</div>

	<section class="space-y-2">
		<p class="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Web & API</p>
		<div class="space-y-3">
			<ChannelCard
				icon={Globe}
				name="Web Widget"
				description="Embed a chat widget on your website with a single script tag."
				bind:enabled={webEnabled}
			>
				{#snippet children()}
					<ChannelConfigWeb instanceId={data.instance.id} />
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

	<section class="space-y-2">
		<p class="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Messaging</p>
		<div class="grid gap-3 md:grid-cols-2">
			<ChannelCard
				icon={MessageSquare}
				name="WhatsApp Business"
				description="Connect via Meta Cloud API. Receives messages and replies through the agent."
				comingSoon
			/>
			<ChannelCard
				icon={Send}
				name="Telegram"
				description="Bot integration with token-based webhook setup."
				comingSoon
			/>
			<ChannelCard
				icon={Hash}
				name="Slack"
				description="Slash commands and DMs in your workspace."
				comingSoon
			/>
			<ChannelCard
				icon={Phone}
				name="SMS"
				description="Inbound and outbound SMS via Twilio or compatible providers."
				comingSoon
			/>
		</div>
	</section>

	<section class="space-y-2">
		<p class="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Email & Integrations</p>
		<div class="grid gap-3 md:grid-cols-2">
			<ChannelCard
				icon={Mail}
				name="Email"
				description="Reply to emails routed to a dedicated inbox."
				comingSoon
			/>
			<ChannelCard
				icon={Webhook}
				name="Webhook"
				description="Forward events to any HTTPS endpoint with HMAC signing."
				comingSoon
			/>
		</div>
	</section>
</div>
