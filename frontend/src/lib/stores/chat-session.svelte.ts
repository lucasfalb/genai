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
		this.version += 1;
	}
}

export const chatSessionStore = new ChatSessionRegistry();
