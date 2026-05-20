<script lang="ts">
	import { page } from '$app/state';
	import { PUBLIC_API_BASE_URL } from '$env/static/public';
	import WidgetApp from '$lib/widget/widget-app.svelte';

	const instanceId = page.params.instanceId ?? '';
</script>

<svelte:head>
	<meta name="robots" content="noindex" />
</svelte:head>

<style>
	:global(html, body) {
		margin: 0;
		background: transparent;
	}
</style>

<WidgetApp {instanceId} apiBase={PUBLIC_API_BASE_URL} />
