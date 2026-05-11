<script lang="ts">
	import RunTracePanel from '$lib/components/instance/run-trace-panel.svelte';

	let { data } = $props();
</script>

<RunTracePanel instanceId={data.instance.id} />
