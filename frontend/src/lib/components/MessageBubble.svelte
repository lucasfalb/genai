<script lang="ts">
	import Bot from '@lucide/svelte/icons/bot';
	import User from '@lucide/svelte/icons/user';
	import AlertCircle from '@lucide/svelte/icons/alert-circle';

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

	function renderInline(text: string): string {
		const escaped = text
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;');
		return escaped
			.replace(/`([^`]+)`/g, '<code class="rounded bg-black/20 px-1 py-0.5 font-mono text-[11px]">$1</code>')
			.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
			.replace(/\*([^*]+)\*/g, '<em>$1</em>')
			.replace(/\n/g, '<br />');
	}

	const html = $derived(renderInline(content));
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
			<div class="whitespace-pre-wrap break-words text-left">
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
