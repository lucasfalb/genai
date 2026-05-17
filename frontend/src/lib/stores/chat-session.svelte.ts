import type { LiveNodeStatus } from '$lib/api/types';

const SESSION_KEY = (instanceId: string) => `chat_session_${instanceId}`;
const RUN_KEY = (instanceId: string) => `chat_last_run_${instanceId}`;

function read(key: string): string | null {
	if (typeof sessionStorage === 'undefined') return null;
	return sessionStorage.getItem(key);
}

function write(key: string, value: string): void {
	if (typeof sessionStorage === 'undefined') return;
	sessionStorage.setItem(key, value);
}

function remove(key: string): void {
	if (typeof sessionStorage === 'undefined') return;
	sessionStorage.removeItem(key);
}

class ChatSessionRegistry {
	private version = $state(0);

	// In-memory live run tracking (not persisted)
	private _liveSteps: Record<string, LiveNodeStatus[]> = $state({});
	private _liveRunIds: Record<string, string> = $state({});

	sessionId(instanceId: string): string | null {
		this.version;
		return read(SESSION_KEY(instanceId));
	}

	lastRunId(instanceId: string): string | null {
		this.version;
		return read(RUN_KEY(instanceId));
	}

	setSessionId(instanceId: string, sessionId: string): void {
		if (read(SESSION_KEY(instanceId)) === sessionId) return;
		write(SESSION_KEY(instanceId), sessionId);
		this.version += 1;
	}

	setLastRunId(instanceId: string, runId: string): void {
		if (read(RUN_KEY(instanceId)) === runId) return;
		write(RUN_KEY(instanceId), runId);
		this.version += 1;
	}

	clear(instanceId: string): void {
		remove(SESSION_KEY(instanceId));
		remove(RUN_KEY(instanceId));
		this.clearLiveRun(instanceId);
		this.version += 1;
	}

	// ─── Live run tracking ────────────────────────────────────────────────────

	liveNodeSteps(instanceId: string): LiveNodeStatus[] {
		return this._liveSteps[instanceId] ?? [];
	}

	liveRunId(instanceId: string): string | null {
		return this._liveRunIds[instanceId] ?? null;
	}

	startLiveRun(instanceId: string, runId: string): void {
		this._liveRunIds = { ...this._liveRunIds, [instanceId]: runId };
		this._liveSteps = { ...this._liveSteps, [instanceId]: [] };
	}

	nodeStarted(
		instanceId: string,
		node: { name: string; step: number | null; triggers?: string[] | null }
	): void {
		const current = this._liveSteps[instanceId] ?? [];
		const entry: LiveNodeStatus = { name: node.name, step: node.step, status: 'running', triggers: node.triggers };
		this._liveSteps = { ...this._liveSteps, [instanceId]: [...current, entry] };
	}

	nodeCompleted(
		instanceId: string,
		info: { name: string; step: number | null; duration_ms?: number; error?: string | null }
	): void {
		const current = this._liveSteps[instanceId] ?? [];
		this._liveSteps = {
			...this._liveSteps,
			[instanceId]: current.map((s) =>
				s.name === info.name && s.step === info.step
					? {
							...s,
							status: (info.error ? 'error' : 'completed') as LiveNodeStatus['status'],
							duration_ms: info.duration_ms,
							error: info.error
						}
					: s
			)
		};
	}

	clearLiveRun(instanceId: string): void {
		const { [instanceId]: _s, ...restSteps } = this._liveSteps;
		const { [instanceId]: _r, ...restIds } = this._liveRunIds;
		this._liveSteps = restSteps;
		this._liveRunIds = restIds;
	}
}

export const chatSessionStore = new ChatSessionRegistry();
