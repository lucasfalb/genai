<script lang="ts">
	import MessagesSquare from '@lucide/svelte/icons/messages-square';
	import User from '@lucide/svelte/icons/user';
	import { Button } from '$lib/components/ui/button/index.js';
	import { renderFormattedMessage } from '$lib/utils/rich-message';
	import type { SessionMessageItem } from '$lib/api/types';
	import { messageInitial } from './session-format';

	let {
		selectedSessionId,
		messages,
		loadingMessages,
		messagesLoaded,
		sessionNotFound,
		conversationEl = $bindable(null),
		openMostRecentSession
	}: {
		selectedSessionId: string | null;
		messages: SessionMessageItem[];
		loadingMessages: boolean;
		messagesLoaded: boolean;
		sessionNotFound: boolean;
		conversationEl: HTMLDivElement | null;
		openMostRecentSession: () => void;
	} = $props();
</script>

<div class="min-h-0 flex-1 overflow-y-auto" bind:this={conversationEl}>
	{#if !selectedSessionId}
		<div
			class="flex h-full items-center justify-center p-8 text-center text-sm text-muted-foreground"
		>
			Select a session to view the transcript.
		</div>
	{:else if sessionNotFound}
		<div class="flex h-full items-center justify-center p-8">
			<div class="mx-auto max-w-md text-center">
				<div
					class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border bg-muted"
				>
					<MessagesSquare class="h-5 w-5 text-muted-foreground" />
				</div>
				<h3 class="text-lg font-semibold">Session not found</h3>
				<p class="mt-2 text-sm text-muted-foreground">
					This conversation does not exist, was removed, or is not available in the current tenant.
				</p>
				<Button variant="outline" size="sm" class="mt-5" onclick={openMostRecentSession}>
					Open most recent session
				</Button>
			</div>
		</div>
	{:else if loadingMessages || !messagesLoaded}
		<div class="mx-auto flex w-full max-w-5xl flex-col gap-5 px-5 py-6" aria-busy="true">
			{#each Array.from({ length: 5 }) as _, index}
				<div class="flex gap-3 {index % 3 === 0 ? 'justify-end' : 'justify-start'}">
					{#if index % 3 !== 0}
						<div
							class="glass-panel h-9 w-9 shrink-0 animate-pulse rounded-full border"
							style="border-color:var(--ds-border-hover)"
						></div>
					{/if}
					<div
						class="glass-panel min-h-[64px] animate-pulse border"
						class:w-[min(680px,78%)]={index % 3 !== 0}
						class:w-[min(360px,58%)]={index % 3 === 0}
						style="border-color:var(--ds-border)"
					>
						<div class="space-y-2 p-4">
							<div class="h-3 w-11/12 bg-muted"></div>
							<div class="h-3 w-8/12 bg-muted"></div>
							{#if index === 1 || index === 4}
								<div class="h-3 w-10/12 bg-muted"></div>
							{/if}
						</div>
					</div>
					{#if index % 3 === 0}
						<div
							class="glass-panel h-9 w-9 shrink-0 animate-pulse rounded-full border"
							style="border-color:var(--ds-border-hover)"
						></div>
					{/if}
				</div>
			{/each}
		</div>
	{:else if messages.length === 0}{:else}
		<div class="mx-auto flex w-full max-w-5xl flex-col gap-5 px-5 py-6">
			{#each messages as msg (msg.id)}
				<div class="flex gap-3 {msg.role === 'user' ? 'justify-end' : 'justify-start'}">
					{#if msg.role !== 'user'}
						<div
							class="glass-panel flex h-9 w-9 shrink-0 items-center justify-center rounded-full border text-xs font-semibold"
							style="border-color:var(--ds-border-hover)"
						>
							{messageInitial(msg.role)}
						</div>
					{/if}
					<div
						class="max-w-[min(780px,82%)] border px-4 py-3 text-sm leading-relaxed"
						style={msg.role === 'user'
							? 'background:var(--text-main);border-color:var(--text-main);color:var(--canvas)'
							: 'background:color-mix(in srgb,var(--text-main) 6%,transparent);border-color:var(--ds-border-hover);color:var(--text-main)'}
					>
						<div class="session-rich-message">
							{@html renderFormattedMessage(msg.content)}
						</div>
					</div>
					{#if msg.role === 'user'}
						<div
							class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border text-xs font-semibold"
							style="background:var(--text-main);border-color:var(--text-main);color:var(--canvas)"
						>
							<User class="h-4 w-4" />
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.session-rich-message {
		white-space: normal;
	}
	.session-rich-message :global(p) {
		margin: 0 0 0.72em;
	}
	.session-rich-message :global(p:last-child),
	.session-rich-message :global(ul:last-child),
	.session-rich-message :global(h3:last-child),
	.session-rich-message :global(h4:last-child) {
		margin-bottom: 0;
	}
	.session-rich-message :global(ul) {
		margin: 0.35em 0 0.8em;
		padding-left: 1.2em;
	}
	.session-rich-message :global(li) {
		margin: 0.22em 0;
		padding-left: 0.1em;
	}
	.session-rich-message :global(strong) {
		font-weight: 750;
	}
	.session-rich-message :global(code) {
		border-radius: 6px;
		background: rgba(15, 23, 42, 0.12);
		padding: 0.1em 0.34em;
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 0.92em;
	}
	.session-rich-message :global(a) {
		color: inherit;
		font-weight: 700;
		text-decoration: underline;
		text-underline-offset: 2px;
	}
	.session-rich-message :global(h3),
	.session-rich-message :global(h4) {
		margin: 0.1em 0 0.45em;
		font-size: 1em;
		line-height: 1.35;
		font-weight: 800;
	}
</style>
