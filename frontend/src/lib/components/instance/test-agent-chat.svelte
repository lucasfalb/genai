<script lang="ts">
	import { onDestroy, untrack } from 'svelte';
	import Bot from '@lucide/svelte/icons/bot';
	import Database from '@lucide/svelte/icons/database';
	import RefreshCcw from '@lucide/svelte/icons/refresh-ccw';
	import Send from '@lucide/svelte/icons/send';
	import Square from '@lucide/svelte/icons/square';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import MessageBubble from '$lib/components/MessageBubble.svelte';
	import { streamChat, chatSession, tracesApi, type ChatStreamError } from '$lib/api/chat';
	import { chatSessionStore } from '$lib/stores/chat-session.svelte';
	import { getErrorMessage } from '$lib/api/client';
	import type { GraphNodeEventPayload, RunTraceResponse } from '$lib/api/types';

	const NODE_LABELS: Record<string, string> = {
		rag: 'Buscando contexto',
		llm: 'Processando',
		dispatch: 'Executando ferramenta',
		handoff: 'Transferindo sessão'
	};

	type ChatMessage = {
		id: string;
		role: 'user' | 'assistant' | 'error';
		content: string;
		timestamp: Date;
		isStreaming?: boolean;
		hint?: string;
	};

	let {
		instanceId,
		instanceName,
		collectionsHref,
		sessionId: propSessionId
	}: {
		instanceId: string;
		instanceName: string;
		collectionsHref: string;
		sessionId?: string | null;
	} = $props();

	let messages = $state<ChatMessage[]>([]);
	let input = $state('');
	let isStreaming = $state(false);
	let activeNode = $state<string | null>(null);
	let sessionId = $state<string | null>(null);
	let loadingPast = $state(false);
	let abortController: AbortController | null = null;
	let scrollContainer: HTMLDivElement | null = $state(null);

	$effect(() => {
		instanceId;
		propSessionId;
		untrack(() => {
			const storedSessionId = propSessionId ?? chatSession.get(instanceId);
			sessionId = storedSessionId;
			messages = [];
			input = '';
			isStreaming = false;
			if (storedSessionId) {
				void loadPastMessages(storedSessionId);
			}
		});
	});

	let pastLoadId = 0;

	async function loadPastMessages(storedSessionId: string): Promise<void> {
		const loadId = ++pastLoadId;
		loadingPast = true;
		try {
			const runs = await tracesApi.list(instanceId, storedSessionId, 100);
			runs.sort((a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime());
			const traces: RunTraceResponse[] = [];
			for (const run of runs) {
				try {
					traces.push(await tracesApi.get(instanceId, run.run_id));
				} catch {
					// skip individual failures
				}
			}
			if (loadId !== pastLoadId) return;
			const loaded: ChatMessage[] = [];
			for (const t of traces) {
				if (t.trace.user_message) {
					loaded.push({
						id: `user-${t.run_id}`,
						role: 'user',
						content: t.trace.user_message,
						timestamp: new Date(t.created_at)
					});
				}
				if (t.trace.final_response) {
					loaded.push({
						id: `assistant-${t.run_id}`,
						role: 'assistant',
						content: t.trace.final_response,
						timestamp: new Date(t.created_at)
					});
				}
			}
			if (loadId === pastLoadId && messages.length === 0) {
				messages = loaded;
			}
		} catch {
			if (loadId === pastLoadId && messages.length === 0) {
				messages = [];
			}
		} finally {
			if (loadId === pastLoadId) {
				loadingPast = false;
			}
		}
	}

	$effect(() => {
		if (!scrollContainer) return;
		messages.length;
		queueMicrotask(() => {
			if (scrollContainer) {
				scrollContainer.scrollTop = scrollContainer.scrollHeight;
			}
		});
	});

	onDestroy(() => {
		abortController?.abort();
	});

	function uid(): string {
		return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
	}

	function pushMessage(
		msg: Omit<ChatMessage, 'id' | 'timestamp'> & { id?: string; timestamp?: Date }
	): ChatMessage {
		const created: ChatMessage = {
			id: msg.id ?? uid(),
			role: msg.role,
			content: msg.content,
			timestamp: msg.timestamp ?? new Date(),
			isStreaming: msg.isStreaming ?? false,
			hint: msg.hint
		};
		messages = [...messages, created];
		return created;
	}

	function updateMessage(id: string, patch: Partial<ChatMessage>): void {
		messages = messages.map((m) => (m.id === id ? { ...m, ...patch } : m));
	}

	function errorMessageFor(error: ChatStreamError): string {
		if (error.status === 409)
			return 'O agente esta processando outra mensagem. Aguarde alguns segundos e tente novamente.';
		if (error.status === 502)
			return 'Provedor de IA indisponivel. Verifique a configuracao em System Settings ou Tenant AI.';
		if (error.status === 503) return 'Sessao bloqueada (lock). Tente novamente em instantes.';
		if (error.status === 401) return 'Sessao expirada. Faca login novamente.';
		if (error.status === 0) return error.message ?? 'Conexao interrompida.';
		return error.message ?? 'Falha ao enviar mensagem.';
	}

	async function send(): Promise<void> {
		const text = input.trim();
		if (!text || isStreaming) return;

		const tempRunId = `live-${Date.now()}`;
		chatSessionStore.startLiveRun(instanceId, tempRunId);

		input = '';
		isStreaming = true;
		pushMessage({ role: 'user', content: text });
		const assistant = pushMessage({ role: 'assistant', content: '', isStreaming: true });

		abortController?.abort();
		abortController = new AbortController();

		await streamChat(
			instanceId,
			{
				message: text,
				session_id: sessionId ?? undefined,
				channel: 'api'
			},
			{
				onAssistantDelta: (content) => {
					updateMessage(assistant.id, { content });
				},
				onNodeStarted: (node: GraphNodeEventPayload) => {
					activeNode = node.name;
					chatSessionStore.nodeStarted(instanceId, { name: node.name, step: node.step, triggers: node.triggers });
				},
				onNodeCompleted: (node: GraphNodeEventPayload) => {
					chatSessionStore.nodeCompleted(instanceId, { name: node.name, step: node.step, duration_ms: node.duration_ms, error: node.error });
				},
				onTrace: (_trace, event) => {
					const runId = (event.metadata as { run_id?: string } | undefined)?.run_id;
					if (runId) chatSession.setLastRunId(instanceId, runId);
				},
				onCompleted: (event) => {
					activeNode = null;
					sessionId = event.session_id;
					chatSession.set(instanceId, event.session_id);
					const runId = (event.metadata as { run_id?: string } | undefined)?.run_id;
					if (runId) chatSession.setLastRunId(instanceId, runId);
					updateMessage(assistant.id, { isStreaming: false });
					// Clear live run after a short delay so the panel can show the full trace
					setTimeout(() => chatSessionStore.clearLiveRun(instanceId), 2000);
				},
				onError: (error) => {
					activeNode = null;
					chatSessionStore.clearLiveRun(instanceId);
					updateMessage(assistant.id, {
						role: 'error',
						content: errorMessageFor(error),
						isStreaming: false,
						hint: error.code ? `error code: ${error.code}` : undefined
					});
				}
			},
			abortController.signal
		);

		isStreaming = false;
		abortController = null;
	}

	function cancel(): void {
		abortController?.abort();
		abortController = null;
		isStreaming = false;
		activeNode = null;
		chatSessionStore.clearLiveRun(instanceId);
		messages = messages.map((m) => (m.isStreaming ? { ...m, isStreaming: false } : m));
	}

	function resetSession(): void {
		abortController?.abort();
		abortController = null;
		isStreaming = false;
		activeNode = null;
		chatSession.clear(instanceId);
		sessionId = null;
		messages = [];
		input = '';
	}

	function handleKeydown(event: KeyboardEvent): void {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			send();
		}
	}
</script>

<aside class="flex h-full flex-col overflow-hidden bg-[var(--surface)]">
	<header
		class="flex h-14 shrink-0 items-center justify-between border-b px-5"
		style="border-color:var(--ds-border)"
	>
		<div class="flex items-center gap-2">
			<Bot class="size-4 text-muted-foreground" />
			<h2 class="text-sm font-semibold" style="color:var(--text-main)">Test agent</h2>
			{#if sessionId}
				<span
					class="rounded bg-blue-500/10 px-1.5 py-0.5 font-mono text-[9px] tracking-wider text-blue-400"
					title={`session ${sessionId}`}
				>
					session #{sessionId.slice(0, 6)}
				</span>
			{/if}
		</div>
		<div class="flex items-center gap-1">
			<a
				href={collectionsHref}
				class="rounded p-1.5 text-muted-foreground transition-colors hover:bg-[var(--surface-hover)] hover:text-foreground"
				title="Collections & Knowledge"
			>
				<Database class="size-4" />
			</a>
			<button
				type="button"
				onclick={resetSession}
				class="rounded p-1.5 text-muted-foreground transition-colors hover:bg-[var(--surface-hover)] hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
				title="Reset session"
				disabled={messages.length === 0 && !sessionId}
				aria-label="Reset chat session"
			>
				<RefreshCcw class="size-4" />
			</button>
		</div>
	</header>

	<div
		bind:this={scrollContainer}
		class="flex flex-1 flex-col gap-4 overflow-y-auto p-4"
		role="log"
		aria-live="polite"
	>
		{#if loadingPast}
			<div class="flex flex-1 items-center justify-center text-sm text-muted-foreground">
				<Spinner class="mr-2 size-4" />
				Loading messages…
			</div>
		{:else if messages.length === 0}{:else}
			{#each messages as message (message.id)}
				<MessageBubble
					role={message.role}
					content={message.content}
					isStreaming={message.isStreaming}
					timestamp={message.timestamp}
					hint={message.hint}
				/>
			{/each}
			{#if isStreaming && activeNode && !messages[messages.length - 1]?.content}
				<div class="flex items-center gap-2 pl-11 text-xs text-muted-foreground">
					<Spinner class="size-3" />
					<span>{NODE_LABELS[activeNode] ?? 'Processando'}…</span>
				</div>
			{:else if isStreaming && !activeNode && messages[messages.length - 1]?.role === 'assistant' && !messages[messages.length - 1]?.content}
				<div class="flex items-center gap-2 pl-11 text-xs text-muted-foreground">
					<Spinner class="size-3" />
					<span>Iniciando…</span>
				</div>
			{/if}
			{#if isStreaming && activeNode && messages[messages.length - 1]?.content}
				<div class="flex items-center gap-1.5 pl-11 text-[10px] text-muted-foreground/60">
					<Spinner class="size-2.5" />
					<span class="font-mono">{activeNode}</span>
				</div>
			{/if}
		{/if}
	</div>

	<div class="shrink-0 border-t p-4" style="border-color:var(--ds-border)">
		<div
			class="rounded-xl border bg-[var(--canvas)] p-3 shadow-sm focus-within:ring-1 focus-within:ring-blue-500/30"
			style="border-color:var(--ds-border)"
		>
			<textarea
				bind:value={input}
				onkeydown={handleKeydown}
				rows="3"
				maxlength="2000"
				disabled={isStreaming}
				placeholder="..."
				class="w-full resize-none bg-transparent text-sm outline-none placeholder:text-muted-foreground disabled:opacity-60"
			></textarea>
			<div class="mt-2 flex items-center justify-between">
				<span class="font-mono text-[10px] text-muted-foreground">{input.length}/2000</span>
				{#if isStreaming}
					<button
						type="button"
						onclick={cancel}
						class="inline-flex items-center gap-1.5 rounded-md bg-zinc-700 px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-zinc-600"
						aria-label="Cancel streaming"
					>
						<Square class="size-3.5" />
						Parar
					</button>
				{:else}
					<button
						type="button"
						onclick={send}
						disabled={!input.trim()}
						class="inline-flex size-8 items-center justify-center rounded-md bg-blue-600 text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40"
						aria-label="Send test message"
					>
						<Send class="size-4" />
					</button>
				{/if}
			</div>
		</div>
	</div>
</aside>
