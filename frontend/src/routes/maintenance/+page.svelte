<script lang="ts">
	import Bot from '@lucide/svelte/icons/bot';
	import Wrench from '@lucide/svelte/icons/wrench';

	let { data } = $props();
	const platformName = $derived(data.publicSettings.platform_name || 'GENAI');
</script>

<svelte:head>
	<title>{platformName} — Maintenance</title>
</svelte:head>

<div
	class="flex min-h-screen flex-col items-center justify-center gap-6 px-6 text-center"
	style="background:var(--canvas);color:var(--text-main)"
>
	<div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-500/10">
		<Wrench class="h-7 w-7 text-amber-400" />
	</div>

	<div class="space-y-2">
		<div class="flex items-center justify-center gap-2 text-muted-foreground">
			<Bot class="h-4 w-4" />
			<span class="text-sm font-semibold tracking-widest uppercase">{platformName}</span>
		</div>
		<h1 class="font-display text-2xl font-semibold" style="color:var(--text-main)">
			Under Maintenance
		</h1>
		<p class="max-w-sm text-sm text-muted-foreground">
			We're making improvements to the platform. Please check back shortly.
		</p>
	</div>

	<a
		href="/login"
		class="text-xs text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
	>
		Sign in as administrator
	</a>
</div>
