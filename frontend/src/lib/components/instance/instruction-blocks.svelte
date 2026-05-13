<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import X from '@lucide/svelte/icons/x';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import * as Accordion from '$lib/components/ui/accordion/index.js';
	import type { AgentInstructionBlock } from '$lib/api/types';

	let { blocks = $bindable() }: { blocks: AgentInstructionBlock[] } = $props();

	let newBlock = $state({ topic: '', title: '', content: '', priority: 10, is_enabled: true });
	let adding = $state(false);
	let openItem = $state<string | undefined>(undefined);

	function genId(): string {
		return `ib_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
	}

	function add() {
		if (!newBlock.topic.trim() || !newBlock.content.trim()) return;
		blocks = [
			...blocks,
			{
				id: genId(),
				...newBlock,
				topic: newBlock.topic.trim(),
				title: newBlock.title.trim(),
				content: newBlock.content.trim()
			}
		];
		newBlock = { topic: '', title: '', content: '', priority: 10, is_enabled: true };
		adding = false;
	}

	function remove(i: number) {
		blocks = blocks.filter((_, idx) => idx !== i);
	}

	function move(i: number, dir: -1 | 1) {
		const j = i + dir;
		if (j < 0 || j >= blocks.length) return;
		const arr = [...blocks];
		[arr[i], arr[j]] = [arr[j], arr[i]];
		blocks = arr;
	}

	function toggle(i: number) {
		blocks = blocks.map((b, idx) => (idx === i ? { ...b, is_enabled: !b.is_enabled } : b));
	}

	function update(i: number, patch: Partial<AgentInstructionBlock>) {
		blocks = blocks.map((b, idx) => (idx === i ? { ...b, ...patch } : b));
	}
</script>

<div class="p-6" style="background:var(--surface);border:1px solid var(--ds-border)">
	<div class="mb-4 flex items-center justify-between">
		<div>
			<h3 class="font-display text-sm font-semibold" style="color:var(--text-main)">
				Instruction blocks
			</h3>
			<p class="mt-0.5 text-xs text-muted-foreground">
				Custom instruction sections injected into the prompt
			</p>
		</div>
		<Button variant="ghost" size="sm" onclick={() => (adding = !adding)}>
			<Plus data-icon="inline-start" />
			Add block
		</Button>
	</div>

	{#if adding}
		<div
			class="mb-4 space-y-3 rounded-lg p-4"
			style="background:var(--surface-hover);border:1px solid var(--ds-border-hover)"
		>
			<div class="grid grid-cols-2 gap-3">
				<div class="space-y-1">
					<label
						class="block text-[10px] font-semibold tracking-widest text-muted-foreground uppercase"
						>Topic *</label
					>
					<Input bind:value={newBlock.topic} placeholder="e.g. tone" />
				</div>
				<div class="space-y-1">
					<label
						class="block text-[10px] font-semibold tracking-widest text-muted-foreground uppercase"
						>Title</label
					>
					<Input bind:value={newBlock.title} placeholder="Display title" />
				</div>
			</div>
			<div class="space-y-1">
				<label
					class="block text-[10px] font-semibold tracking-widest text-muted-foreground uppercase"
					>Content *</label
				>
				<Textarea
					bind:value={newBlock.content}
					rows={3}
					placeholder="Instruction text..."
					class="font-mono"
				/>
			</div>
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-2">
					<label class="text-[10px] font-semibold tracking-widest text-muted-foreground uppercase"
						>Priority</label
					>
					<Input
						type="number"
						bind:value={newBlock.priority}
						min={1}
						max={100}
						class="w-16 text-center font-mono"
					/>
				</div>
				<div class="flex gap-2">
					<Button variant="ghost" size="sm" onclick={() => (adding = false)}>Cancel</Button>
					<Button size="sm" onclick={add}>Add</Button>
				</div>
			</div>
		</div>
	{/if}

	{#if blocks.length === 0}
		<p class="py-4 text-center text-sm text-muted-foreground">No instruction blocks yet.</p>
	{:else}
		<Accordion.Root type="single" bind:value={openItem} class="space-y-2">
			{#each blocks as blk, i (i)}
				{@const itemValue = `block-${i}`}
				<Accordion.Item
					value={itemValue}
					class="rounded-lg border-b-0 px-3 py-1"
					style="background:var(--surface-hover);border:1px solid var(--ds-border);opacity:{blk.is_enabled
						? 1
						: 0.5}"
				>
					<div class="flex items-center gap-2 py-2">
						<Accordion.Trigger class="flex flex-1 items-center gap-2 hover:no-underline">
							<ChevronDown
								class="size-4 text-muted-foreground transition-transform"
								data-accordion-chevron
							/>
							<span class="font-mono text-sm font-semibold" style="color:var(--text-main)"
								>{blk.topic || '(no topic)'}</span
							>
							{#if blk.title}<span class="truncate text-xs text-muted-foreground"
									>— {blk.title}</span
								>{/if}
							<Badge variant="outline" class="ml-auto font-mono text-[10px]">p{blk.priority}</Badge>
						</Accordion.Trigger>
						<div class="ml-auto flex shrink-0 items-center gap-1">
							<Button variant="ghost" size="icon-xs" disabled={i === 0} onclick={() => move(i, -1)}>
								<ArrowUp />
							</Button>
							<Button
								variant="ghost"
								size="icon-xs"
								disabled={i === blocks.length - 1}
								onclick={() => move(i, 1)}
							>
								<ArrowDown />
							</Button>
							<Switch checked={blk.is_enabled} onCheckedChange={() => toggle(i)} />
							<Button variant="ghost" size="icon-xs" onclick={() => remove(i)}>
								<X />
							</Button>
						</div>
					</div>
					<Accordion.Content class="space-y-2 pb-3">
						<div class="grid grid-cols-2 gap-2">
							<Input
								value={blk.topic}
								oninput={(e) => update(i, { topic: e.currentTarget.value })}
								placeholder="Topic"
							/>
							<Input
								value={blk.title}
								oninput={(e) => update(i, { title: e.currentTarget.value })}
								placeholder="Title (optional)"
							/>
						</div>
						<Textarea
							value={blk.content}
							oninput={(e) => update(i, { content: e.currentTarget.value })}
							rows={4}
							placeholder="Instruction content"
							class="resize-y font-mono text-xs"
						/>
					</Accordion.Content>
				</Accordion.Item>
			{/each}
		</Accordion.Root>
	{/if}
</div>
