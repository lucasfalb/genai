import { PUBLIC_API_BASE_URL } from '$env/static/public';
import { authStore } from '$lib/stores/auth.svelte';
import { tenantStore } from '$lib/stores/tenant.svelte';
import { api } from '$lib/api/client';
import type {
	ChatEvent,
	ChatRequest,
	RunTraceListItem,
	RunTracePayload,
	RunTraceResponse
} from '$lib/api/types';

export interface ChatStreamError {
	status: number;
	message: string;
	code?: string;
}

export interface ChatStreamCallbacks {
	onEvent?: (event: ChatEvent) => void;
	onUserPersisted?: (event: ChatEvent) => void;
	onAssistantDelta?: (content: string, event: ChatEvent) => void;
	onTrace?: (trace: RunTracePayload, event: ChatEvent) => void;
	onCompleted?: (event: ChatEvent) => void;
	onError?: (error: ChatStreamError) => void;
}

export async function streamChat(
	instanceId: string,
	body: ChatRequest,
	callbacks: ChatStreamCallbacks,
	signal?: AbortSignal
): Promise<void> {
	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		Accept: 'text/event-stream'
	};
	if (authStore.accessToken) headers['Authorization'] = `Bearer ${authStore.accessToken}`;
	if (tenantStore.activeTenantId) headers['X-Tenant-ID'] = tenantStore.activeTenantId;

	let response: Response;
	try {
		response = await fetch(`${PUBLIC_API_BASE_URL}/agent/instances/${instanceId}/chat`, {
			method: 'POST',
			headers,
			body: JSON.stringify(body),
			signal
		});
	} catch (err) {
		if ((err as { name?: string }).name === 'AbortError') return;
		callbacks.onError?.({ status: 0, message: (err as Error).message ?? 'Network error' });
		return;
	}

	if (!response.ok) {
		let payload: { error?: { code?: string; message?: string }; message?: string } = {};
		try {
			payload = await response.json();
		} catch {
			/* non-json error */
		}
		callbacks.onError?.({
			status: response.status,
			message: payload.error?.message ?? payload.message ?? response.statusText ?? 'Request failed',
			code: payload.error?.code
		});
		return;
	}

	if (!response.body) {
		callbacks.onError?.({ status: response.status, message: 'Empty response stream' });
		return;
	}

	const reader = response.body.getReader();
	const decoder = new TextDecoder('utf-8');
	let buffer = '';

	try {
		while (true) {
			const { value, done } = await reader.read();
			if (done) break;
			buffer += decoder.decode(value, { stream: true });

			let sep = buffer.indexOf('\n\n');
			while (sep !== -1) {
				const block = buffer.slice(0, sep);
				buffer = buffer.slice(sep + 2);
				dispatchSseBlock(block, callbacks);
				sep = buffer.indexOf('\n\n');
			}
		}
		const tail = buffer.trim();
		if (tail) dispatchSseBlock(tail, callbacks);
	} catch (err) {
		if ((err as { name?: string }).name === 'AbortError') return;
		callbacks.onError?.({ status: 0, message: (err as Error).message ?? 'Stream interrupted' });
	} finally {
		try {
			reader.releaseLock();
		} catch {
			/* ignore */
		}
	}
}

function dispatchSseBlock(block: string, callbacks: ChatStreamCallbacks): void {
	const dataLines: string[] = [];
	for (const rawLine of block.split('\n')) {
		const line = rawLine.replace(/\r$/, '');
		if (!line || line.startsWith(':')) continue;
		if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart());
	}
	if (dataLines.length === 0) return;
	const payload = dataLines.join('\n');
	let event: ChatEvent;
	try {
		event = JSON.parse(payload) as ChatEvent;
	} catch {
		return;
	}
	callbacks.onEvent?.(event);
	switch (event.event) {
		case 'message.persisted':
			callbacks.onUserPersisted?.(event);
			break;
		case 'assistant.delta':
			if (typeof event.content === 'string') {
				callbacks.onAssistantDelta?.(event.content, event);
			}
			break;
		case 'run.trace': {
			const trace = (event.metadata as { trace?: RunTracePayload } | undefined)?.trace;
			if (trace) callbacks.onTrace?.(trace, event);
			break;
		}
		case 'run.completed':
			callbacks.onCompleted?.(event);
			break;
	}
}

import { chatSessionStore } from '$lib/stores/chat-session.svelte';

export const chatSession = {
	get(instanceId: string): string | null {
		return chatSessionStore.sessionId(instanceId);
	},
	set(instanceId: string, sessionId: string): void {
		chatSessionStore.setSessionId(instanceId, sessionId);
	},
	clear(instanceId: string): void {
		chatSessionStore.clear(instanceId);
	},
	getLastRunId(instanceId: string): string | null {
		return chatSessionStore.lastRunId(instanceId);
	},
	setLastRunId(instanceId: string, runId: string): void {
		chatSessionStore.setLastRunId(instanceId, runId);
	}
};

export const tracesApi = {
	getLatest: (instanceId: string, sessionId?: string | null) =>
		api.get<RunTraceResponse>(
			`/agent/instances/${instanceId}/runs/latest`,
			sessionId ? { session_id: sessionId } : undefined
		),
	get: (instanceId: string, runId: string) =>
		api.get<RunTraceResponse>(`/agent/instances/${instanceId}/runs/${runId}`),
	list: (instanceId: string, sessionId?: string | null, limit = 20) => {
		const params: Record<string, string> = { limit: String(limit) };
		if (sessionId) params.session_id = sessionId;
		return api.get<RunTraceListItem[]>(`/agent/instances/${instanceId}/runs`, params);
	}
};
