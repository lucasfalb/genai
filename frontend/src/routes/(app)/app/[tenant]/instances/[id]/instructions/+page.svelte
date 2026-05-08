<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import InstructionBlocks from '$lib/components/instance/instruction-blocks.svelte';
	import Guardrails from '$lib/components/instance/guardrails.svelte';
	import { instancesApi } from '$lib/api/instances';
	import { getErrorMessage } from '$lib/api/client';
	import type {
		AgentPromptConfigResponse,
		AgentInstructionBlock,
		AgentGuardrail
	} from '$lib/api/types';

	let { data } = $props();

	const { register, unregister, setSaving } = getContext<{
		register: (handler: () => Promise<void>, label: string) => void;
		unregister: () => void;
		setSaving: (v: boolean) => void;
	}>('save-action');

	let promptConfig = $state<AgentPromptConfigResponse>(data.promptConfig);
	let blocks = $state<AgentInstructionBlock[]>([...(data.promptConfig.instruction_blocks ?? [])]);
	let guardrails = $state<AgentGuardrail[]>([...(data.promptConfig.guardrails ?? [])]);

	async function save() {
		setSaving(true);
		try {
			const normalizedBlocks = blocks
				.filter((b) => b.topic.trim() && b.content.trim())
				.map((b, index) => ({
					...b,
					topic: b.topic.trim(),
					title: b.title?.trim() ?? '',
					content: b.content.trim(),
					priority: index + 1
				}));
			const normalizedGuardrails = guardrails
				.filter((g) => g.category.trim() && g.rule.trim())
				.map((g) => ({ ...g, category: g.category.trim(), rule: g.rule.trim() }));
			const cfg = await instancesApi.savePromptConfig(data.instance.id, {
				instruction_blocks: normalizedBlocks,
				guardrails: normalizedGuardrails
			});
			promptConfig = cfg;
			blocks = [...(cfg.instruction_blocks ?? [])];
			guardrails = [...(cfg.guardrails ?? [])];
			toast.success('Instructions saved.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Save failed.'));
		} finally {
			setSaving(false);
		}
	}

	onMount(() => {
		register(save, 'Save instructions');
		return () => unregister();
	});
</script>

<div class="mx-auto max-w-2xl space-y-6 px-6 py-5">
	<InstructionBlocks bind:blocks />
	<Guardrails bind:guardrails />
</div>
