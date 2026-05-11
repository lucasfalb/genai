<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import X from '@lucide/svelte/icons/x';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { NativeSelect } from '$lib/components/ui/native-select/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import * as Accordion from '$lib/components/ui/accordion/index.js';
	import type { AgentGuardrail } from '$lib/api/types';

	let { guardrails = $bindable() }: { guardrails: AgentGuardrail[] } = $props();

	let newGuardrail = $state({ category: 'safety', rule: '', severity: 'warning', is_enabled: true });
	let adding = $state(false);
	let openItem = $state<string | undefined>(undefined);

	const SEVERITY = ['info', 'warning', 'critical', 'blocking'];

	function genId(): string {
		return `g_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
	}

	function severityVariant(s: string): 'default' | 'secondary' | 'outline' | 'destructive' {
		if (s === 'critical' || s === 'blocking') return 'destructive';
		if (s === 'warning') return 'default';
		return 'outline';
	}

	function add() {
		if (!newGuardrail.rule.trim()) return;
		guardrails = [...guardrails, { id: genId(), ...newGuardrail, rule: newGuardrail.rule.trim() }];
		newGuardrail = { category: 'safety', rule: '', severity: 'warning', is_enabled: true };
		adding = false;
	}

	function remove(i: number) { guardrails = guardrails.filter((_, idx) => idx !== i); }

	function toggle(i: number) {
		guardrails = guardrails.map((g, idx) => idx === i ? { ...g, is_enabled: !g.is_enabled } : g);
	}

	function update(i: number, patch: Partial<AgentGuardrail>) {
		guardrails = guardrails.map((g, idx) => idx === i ? { ...g, ...patch } : g);
	}
</script>

<div class="rounded-xl p-6" style="background:var(--surface);border:1px solid var(--ds-border)">
	<div class="mb-4 flex items-center justify-between">
		<div>
			<h3 class="font-display text-sm font-semibold" style="color:var(--text-main)">Guardrails</h3>
			<p class="mt-0.5 text-xs text-muted-foreground">Rules to constrain agent behaviour</p>
		</div>
		<Button variant="ghost" size="sm" onclick={() => (adding = !adding)}>
			<Plus data-icon="inline-start" />
			Add rule
		</Button>
	</div>

	{#if adding}
		<div class="mb-4 rounded-lg p-4 space-y-3" style="background:var(--surface-hover);border:1px solid var(--ds-border-hover)">
			<div class="grid grid-cols-2 gap-3">
				<div class="space-y-1">
					<label class="block text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">Category</label>
					<Input bind:value={newGuardrail.category} />
				</div>
				<div class="space-y-1">
					<label class="block text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">Severity</label>
					<NativeSelect bind:value={newGuardrail.severity} class="w-full">
						{#each SEVERITY as s (s)}<option value={s}>{s}</option>{/each}
					</NativeSelect>
				</div>
			</div>
			<div class="space-y-1">
				<label class="block text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">Rule *</label>
				<Textarea bind:value={newGuardrail.rule} rows={2} placeholder="Never discuss..." />
			</div>
			<div class="flex justify-end gap-2">
				<Button variant="ghost" size="sm" onclick={() => (adding = false)}>Cancel</Button>
				<Button size="sm" onclick={add}>Add</Button>
			</div>
		</div>
	{/if}

	{#if guardrails.length === 0}
		<p class="py-4 text-center text-sm text-muted-foreground">No guardrails configured.</p>
	{:else}
		<Accordion.Root type="single" bind:value={openItem} class="space-y-2">
			{#each guardrails as g, i (i)}
				{@const itemValue = `guardrail-${i}`}
				<Accordion.Item
					value={itemValue}
					class="rounded-lg border-b-0 px-3 py-1"
					style="background:var(--surface-hover);border:1px solid var(--ds-border);opacity:{g.is_enabled ? 1 : 0.5}"
				>
					<div class="flex items-center gap-2 py-2">
						<Accordion.Trigger class="flex flex-1 items-center gap-2 hover:no-underline">
							<ChevronDown class="size-4 text-muted-foreground transition-transform" data-accordion-chevron />
							<span class="text-sm font-semibold" style="color:var(--text-main)">{g.category || '(no category)'}</span>
							<Badge variant={severityVariant(g.severity)} class="ml-2 text-[10px] uppercase">{g.severity}</Badge>
							<span class="ml-auto truncate text-xs text-muted-foreground line-clamp-1">{g.rule}</span>
						</Accordion.Trigger>
						<div class="flex shrink-0 items-center gap-1">
							<Switch checked={g.is_enabled} onCheckedChange={() => toggle(i)} />
							<Button variant="ghost" size="icon-xs" onclick={() => remove(i)}>
								<X />
							</Button>
						</div>
					</div>
					<Accordion.Content class="space-y-2 pb-3">
						<div class="grid grid-cols-2 gap-2">
							<Input
								value={g.category}
								oninput={(e) => update(i, { category: e.currentTarget.value })}
								placeholder="Category"
							/>
							<NativeSelect
								value={g.severity}
								onchange={(e) => update(i, { severity: e.currentTarget.value })}
								class="w-full"
							>
								{#each SEVERITY as s (s)}<option value={s}>{s}</option>{/each}
							</NativeSelect>
						</div>
						<Textarea
							value={g.rule}
							oninput={(e) => update(i, { rule: e.currentTarget.value })}
							rows={3}
							placeholder="Guardrail rule"
							class="resize-y"
						/>
					</Accordion.Content>
				</Accordion.Item>
			{/each}
		</Accordion.Root>
	{/if}
</div>
