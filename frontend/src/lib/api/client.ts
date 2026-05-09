import { PUBLIC_API_BASE_URL } from '$env/static/public';
import { authStore } from '$lib/stores/auth.svelte';
import { tenantStore } from '$lib/stores/tenant.svelte';
import type { ApiErrorPayload, ApiResponse } from './types';

// ─── Error type ───────────────────────────────────────────────────────────────

export class ApiError extends Error {
	constructor(
		public readonly status: number,
		message: string,
		public readonly code?: string,
		public readonly details?: unknown
	) {
		super(message);
		this.name = 'ApiError';
	}
}

export function getErrorMessage(error: unknown, fallback = 'Request failed. Please try again.'): string {
	if (error instanceof ApiError) return error.message;
	if (error instanceof Error && error.message) return error.message;
	return fallback;
}

// ─── Token refresh (single-flight) ────────────────────────────────────────────

let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
	if (refreshPromise) return refreshPromise;

	refreshPromise = (async () => {
		const token = authStore.refreshToken;
		if (!token) return false;
		try {
			const res = await fetch(`${PUBLIC_API_BASE_URL}/auth/refresh`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ refresh_token: token })
			});
			if (!res.ok) return false;
			const json: ApiResponse<{ access_token: string; refresh_token: string }> = await res.json();
			if (json.status !== 'success') return false;
			authStore.setTokens(json.data.access_token, json.data.refresh_token);
			return true;
		} catch {
			return false;
		} finally {
			refreshPromise = null;
		}
	})();

	return refreshPromise;
}

function clearAuthAndRedirect() {
	authStore.clearAuth();
	tenantStore.clearTenant();
	stopProactiveRefresh();
	if (typeof window !== 'undefined') {
		window.location.href = '/login?expired=1';
	}
}

// ─── Proactive refresh ────────────────────────────────────────────────────────

let refreshInterval: ReturnType<typeof setInterval> | null = null;

async function tryRefresh() {
	if (!authStore.isAuthenticated) { stopProactiveRefresh(); return; }
	const ok = await refreshAccessToken();
	if (!ok) clearAuthAndRedirect();
}

export function startProactiveRefresh(intervalMs = 15 * 60 * 1000) {
	stopProactiveRefresh();
	if (typeof window === 'undefined') return;
	refreshInterval = setInterval(() => tryRefresh(), intervalMs);
}

export function stopProactiveRefresh() {
	if (refreshInterval !== null) {
		clearInterval(refreshInterval);
		refreshInterval = null;
	}
}

// ─── Core request ─────────────────────────────────────────────────────────────

async function apiRequest<T>(
	method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE',
	path: string,
	options?: {
		body?: unknown;
		params?: Record<string, string>;
		skipAuth?: boolean;
		skipTenant?: boolean;
	},
	_retry = false
): Promise<T> {
	const headers: Record<string, string> = {
		'Content-Type': 'application/json'
	};

	if (!options?.skipAuth && authStore.accessToken) {
		headers['Authorization'] = `Bearer ${authStore.accessToken}`;
	}
	if (!options?.skipTenant && tenantStore.activeTenantId) {
		headers['X-Tenant-ID'] = tenantStore.activeTenantId;
	}

	let url = `${PUBLIC_API_BASE_URL}${path}`;
	if (options?.params) {
		url += `?${new URLSearchParams(options.params)}`;
	}

	const res = await fetch(url, {
		method,
		headers,
		body: options?.body !== undefined ? JSON.stringify(options.body) : undefined
	});

	// 401 — try refresh once
	if (res.status === 401 && !options?.skipAuth && !_retry) {
		const refreshed = await refreshAccessToken();
		if (refreshed) {
			return apiRequest<T>(method, path, options, true);
		}
		clearAuthAndRedirect();
		throw new ApiError(401, 'Session expired');
	}

	// Non-JSON responses (e.g. 204)
	if (res.status === 204) {
		return undefined as T;
	}

	let json: ApiResponse<T> | ApiErrorPayload;
	try {
		json = await res.json();
	} catch {
		throw new ApiError(res.status, res.statusText || 'Invalid response');
	}

	if (!res.ok || json.status === 'error') {
		const payload = json as ApiErrorPayload;
		const message = payload.error?.message ?? res.statusText ?? 'Request failed';
		throw new ApiError(res.status, message, payload.error?.code, payload.error?.details);
	}

	return json.data;
}

// ─── Public API object ────────────────────────────────────────────────────────

export const api = {
	get: <T>(path: string, params?: Record<string, string>, opts?: { skipAuth?: boolean; skipTenant?: boolean }) =>
		apiRequest<T>('GET', path, { params, skipAuth: opts?.skipAuth ?? false, skipTenant: opts?.skipTenant ?? false }),

	post: <T>(path: string, body?: unknown, opts?: { skipAuth?: boolean; skipTenant?: boolean }) =>
		apiRequest<T>('POST', path, { body, skipAuth: opts?.skipAuth ?? false, skipTenant: opts?.skipTenant ?? false }),

	put: <T>(path: string, body?: unknown, opts?: { skipAuth?: boolean; skipTenant?: boolean }) =>
		apiRequest<T>('PUT', path, { body, skipAuth: opts?.skipAuth ?? false, skipTenant: opts?.skipTenant ?? false }),

	patch: <T>(path: string, body?: unknown, opts?: { skipAuth?: boolean; skipTenant?: boolean }) =>
		apiRequest<T>('PATCH', path, { body, skipAuth: opts?.skipAuth ?? false, skipTenant: opts?.skipTenant ?? false }),

	del: <T = void>(path: string, opts?: { skipAuth?: boolean; skipTenant?: boolean }) =>
		apiRequest<T>('DELETE', path, { skipAuth: opts?.skipAuth ?? false, skipTenant: opts?.skipTenant ?? false }),

	upload: async <T>(path: string, formData: FormData): Promise<T> => {
		const headers: Record<string, string> = {};
		if (authStore.accessToken) headers['Authorization'] = `Bearer ${authStore.accessToken}`;
		if (tenantStore.activeTenantId) headers['X-Tenant-ID'] = tenantStore.activeTenantId;
		const res = await fetch(`${PUBLIC_API_BASE_URL}${path}`, {
			method: 'POST',
			headers,
			body: formData
		});
		if (res.status === 401) {
			const refreshed = await refreshAccessToken();
			if (!refreshed) {
				clearAuthAndRedirect();
				throw new ApiError(401, 'Session expired');
			}
			return api.upload<T>(path, formData);
		}
		let json: ApiResponse<T> | ApiErrorPayload;
		try {
			json = await res.json();
		} catch {
			throw new ApiError(res.status, res.statusText || 'Invalid response');
		}
		if (!res.ok || json.status === 'error') {
			const payload = json as ApiErrorPayload;
			throw new ApiError(
				res.status,
				payload.error?.message ?? res.statusText ?? 'Upload failed',
				payload.error?.code,
				payload.error?.details
			);
		}
		return (json as ApiResponse<T>).data;
	}
};
