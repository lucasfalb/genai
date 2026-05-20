<script lang="ts">
	import Bot from '@lucide/svelte/icons/bot';
	import User from '@lucide/svelte/icons/user';
	import AlertCircle from '@lucide/svelte/icons/alert-circle';
	import { renderFormattedMessage } from '$lib/utils/rich-message';

	type Role = 'user' | 'assistant' | 'system' | 'error';

	let {
		role,
		content,
		isStreaming = false,
		timestamp,
		hint
	}: {
		role: Role;
		content: string;
		isStreaming?: boolean;
		timestamp?: Date;
		hint?: string;
	} = $props();

	const isUser = $derived(role === 'user');
	const isError = $derived(role === 'error');

	const html = $derived(renderFormattedMessage(content));
</script>

<div
	class="flex items-start gap-3 {isUser ? 'flex-row-reverse' : ''}"
	role="listitem"
	aria-label={role}
>
	<div
		class={[
			'flex size-8 shrink-0 items-center justify-center rounded-full',
			isUser
				? 'bg-zinc-500/10 text-zinc-300'
				: isError
					? 'bg-red-500/10 text-red-400'
					: 'bg-blue-500/10 text-blue-500'
		].join(' ')}
	>
		{#if isUser}
			<User class="size-4" />
		{:else if isError}
			<AlertCircle class="size-4" />
		{:else}
			<Bot class="size-4" />
		{/if}
	</div>

	<div class="min-w-0 max-w-[85%] {isUser ? 'text-right' : ''}">
		<div
			class={[
				'inline-block rounded-xl border px-3 py-2 text-sm leading-relaxed',
				isUser
					? 'bg-blue-600/10 text-foreground'
					: isError
						? 'bg-red-500/5 text-red-300'
						: 'bg-[var(--canvas)] text-foreground'
			].join(' ')}
			style="border-color:var(--ds-border)"
		>
			<div class="rich-message break-words text-left">
				{@html html}{#if isStreaming}<span
						class="ml-0.5 inline-block h-3.5 w-1 translate-y-0.5 animate-pulse bg-current align-middle"
						aria-hidden="true"
					></span>{/if}
			</div>
		</div>
		{#if hint}
			<p class="mt-1 text-[10px] text-muted-foreground">{hint}</p>
		{/if}
		{#if timestamp}
			<p class="mt-0.5 text-[10px] text-muted-foreground/70">
				{timestamp.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
			</p>
		{/if}
	</div>
</div>

<style>
	.rich-message {
		white-space: normal;
	}
	.rich-message :global(p) {
		margin: 0 0 0.72em;
	}
	.rich-message :global(p:last-child),
	.rich-message :global(ul:last-child),
	.rich-message :global(h3:last-child),
	.rich-message :global(h4:last-child) {
		margin-bottom: 0;
	}
	.rich-message :global(ul) {
		margin: 0.35em 0 0.8em;
		padding-left: 1.2em;
	}
	.rich-message :global(li) {
		margin: 0.22em 0;
		padding-left: 0.1em;
	}
	.rich-message :global(strong) {
		font-weight: 750;
	}
	.rich-message :global(code) {
		border-radius: 6px;
		background: rgba(15, 23, 42, 0.12);
		padding: 0.1em 0.34em;
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 0.92em;
	}
	.rich-message :global(a) {
		color: inherit;
		font-weight: 700;
		text-decoration: underline;
		text-underline-offset: 2px;
	}
	.rich-message :global(h3),
	.rich-message :global(h4) {
		margin: 0.1em 0 0.45em;
		font-size: 1em;
		line-height: 1.35;
		font-weight: 800;
	}
</style>
