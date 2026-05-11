<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import X from '@lucide/svelte/icons/x';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import * as Accordion from '$lib/components/ui/accordion/index.js';
	import type { AgentConstraint } from '$lib/api/types';

	let { constraints = $bindable() }: { constraints: AgentConstraint[] } = $props();

	let newConstraint = $state({ rule: '', priority: 100, is_enabled: true });
	let adding = $state(false);
	let openItem = $state<string | undefined>(undefined);

	function genId(): string {
		return `c_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
	}

	function add(): void {
		const rule = newConstraint.rule.trim();
		if (!rule) return;
		constraints = [
			...constraints,
			{ id: genId(), rule, priority: newConstraint.priority, is_enabled: newConstraint.is_enabled }
		];
		newConstraint = { rule: '', priority: 100, is_enabled: true };
		adding = false;
	}

	function remove(i: number): void {
		constraints = constraints.filter((_, idx) => idx !== i);
	}

	function toggle(i: number): void {
		constraints = constraints.map((c, idx) =>
			idx === i ? { ...c, is_enabled: !c.is_enabled } : c
		);
	}

	function update(i: number, patch: Partial<AgentConstraint>): void {
		constraints = constraints.map((c, idx) => (idx === i ? { ...c, ...patch } : c));
	}
</script>

<div class="rounded-xl p-6" style="background:var(--surface);border:1px solid var(--ds-border)">
	<div class="mb-4 flex items-center justify-between">
		<div>
			<h3 class="font-display text-sm font-semibold" style="color:var(--text-main)">Constraints</h3>
			<p class="mt-0.5 text-xs text-muted-foreground">
				Rigid system rules appended at the end of the prompt.
			</p>
		</div>
		<Button variant="ghost" size="sm" onclick={() => (adding = !adding)}>
			<Plus data-icon="inline-start" />
			Add constraint
		</Button>
	</div>

	{#if adding}
		<div
			class="mb-4 space-y-3 rounded-lg p-4"
			style="background:var(--surface-hover);border:1px solid var(--ds-border-hover)"
		>
			<div class="grid grid-cols-[1fr_120px] gap-3">
				<div class="space-y-1">
					<label
						class="block text-[10px] font-semibold tracking-widest text-muted-foreground uppercase"
					>
						Rule *
					</label>
					<Textarea
						bind:value={newConstraint.rule}
						rows={2}
						placeholder="Responda sempre em portugues."
					/>
				</div>
				<div class="space-y-1">
					<label
						class="block text-[10px] font-semibold tracking-widest text-muted-foreground uppercase"
					>
						Priority
					</label>
					<input
						type="number"
						min="0"
						max="1000"
						bind:value={newConstraint.priority}
						class="h-9 w-full rounded-md border bg-transparent px-3 text-sm outline-none"
						style="border-color:var(--ds-border)"
					/>
				</div>
			</div>
			<div class="flex justify-end gap-2">
				<Button variant="ghost" size="sm" onclick={() => (adding = false)}>Cancel</Button>
				<Button size="sm" onclick={add}>Add</Button>
			</div>
		</div>
	{/if}

	{#if constraints.length === 0}
		<p class="py-4 text-center text-sm text-muted-foreground">No constraints configured.</p>
	{:else}
		<Accordion.Root type="single" bind:value={openItem} class="space-y-2">
			{#each constraints as c, i (c.id ?? i)}
				{@const itemValue = `constraint-${i}`}
				<Accordion.Item
					value={itemValue}
					class="rounded-lg border-b-0 px-3 py-1"
					style="background:var(--surface-hover);border:1px solid var(--ds-border);opacity:{c.is_enabled
						? 1
						: 0.5}"
				>
					<div class="flex items-center gap-2 py-2">
						<Accordion.Trigger class="flex flex-1 items-center gap-2 hover:no-underline">
							<ChevronDown
								class="size-4 text-muted-foreground transition-transform"
								data-accordion-chevron
							/>
							<span
								class="rounded bg-zinc-500/10 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
							>
								#{c.priority ?? 100}
							</span>
							<span class="ml-1 line-clamp-1 truncate text-xs text-foreground/80">{c.rule}</span>
						</Accordion.Trigger>
						<div class="flex shrink-0 items-center gap-1">
							<Switch checked={c.is_enabled} onCheckedChange={() => toggle(i)} />
							<Button variant="ghost" size="icon-xs" onclick={() => remove(i)}>
								<X />
							</Button>
						</div>
					</div>
					<Accordion.Content class="space-y-2 pb-3">
						<div class="grid grid-cols-[1fr_120px] gap-2">
							<Textarea
								value={c.rule}
								oninput={(e) => update(i, { rule: e.currentTarget.value })}
								rows={3}
								placeholder="Constraint rule"
								class="resize-y"
							/>
							<input
								type="number"
								min="0"
								max="1000"
								value={c.priority}
								oninput={(e) => update(i, { priority: Number(e.currentTarget.value) || 100 })}
								class="h-9 w-full rounded-md border bg-transparent px-3 text-sm outline-none"
								style="border-color:var(--ds-border)"
							/>
						</div>
					</Accordion.Content>
				</Accordion.Item>
			{/each}
		</Accordion.Root>
	{/if}
</div>
