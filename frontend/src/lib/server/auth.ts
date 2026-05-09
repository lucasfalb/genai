import { PUBLIC_API_BASE_URL } from '$env/static/public';
import { redirect, type Cookies } from '@sveltejs/kit';
import type { AuthMeResponse, AuthResponse, TenantAccessResponse } from '$lib/api/types';

export const AUTH_ACCESS_COOKIE = 'genai_access_token';
export const AUTH_REFRESH_COOKIE = 'genai_refresh_token';
export const ACTIVE_TENANT_COOKIE = 'genai_tenant_id';

const COOKIE_OPTIONS = {
	path: '/',
	sameSite: 'lax' as const,
	secure: false,
	httpOnly: false
};

interface ApiEnvelope<T> {
	status: 'success';
	data: T;
}

export interface ServerAuthSession {
	accessToken: string;
	refreshToken: string | null;
	user: AuthMeResponse;
	memberships: TenantAccessResponse[];
	activeTenant: TenantAccessResponse | null;
}

function setAuthCookies(cookies: Cookies, auth: AuthResponse) {
	if (!auth.access_token || !auth.refresh_token) {
		clearAuthCookies(cookies);
		return;
	}
	const maxAge = 60 * 60 * 24 * 30;
	cookies.set(AUTH_ACCESS_COOKIE, auth.access_token, { ...COOKIE_OPTIONS, maxAge });
	cookies.set(AUTH_REFRESH_COOKIE, auth.refresh_token, { ...COOKIE_OPTIONS, maxAge });
}

export function clearAuthCookies(cookies: Cookies) {
	cookies.delete(AUTH_ACCESS_COOKIE, COOKIE_OPTIONS);
	cookies.delete(AUTH_REFRESH_COOKIE, COOKIE_OPTIONS);
	cookies.delete(ACTIVE_TENANT_COOKIE, COOKIE_OPTIONS);
}

async function backendFetch<T>(
	fetcher: typeof fetch,
	path: string,
	accessToken: string
): Promise<T> {
	const response = await fetcher(`${PUBLIC_API_BASE_URL}${path}`, {
		headers: {
			Authorization: `Bearer ${accessToken}`
		}
	});

	if (!response.ok) {
		throw new Error(`Backend request failed with ${response.status}`);
	}

	const payload = (await response.json()) as ApiEnvelope<T>;
	return payload.data;
}

async function refreshSessionToken(
	fetcher: typeof fetch,
	cookies: Cookies,
	refreshToken: string | null
): Promise<AuthResponse | null> {
	if (!refreshToken) return null;

	const response = await fetcher(`${PUBLIC_API_BASE_URL}/auth/refresh`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ refresh_token: refreshToken })
	});

	if (!response.ok) return null;

	const payload = (await response.json()) as ApiEnvelope<AuthResponse>;
	setAuthCookies(cookies, payload.data);
	return payload.data;
}

export async function requireAuthSession(
	fetcher: typeof fetch,
	cookies: Cookies
): Promise<ServerAuthSession> {
	let accessToken = cookies.get(AUTH_ACCESS_COOKIE);
	const refreshToken = cookies.get(AUTH_REFRESH_COOKIE) ?? null;

	if (!accessToken) {
		throw redirect(303, '/login');
	}

	try {
		const [user, memberships] = await Promise.all([
			backendFetch<AuthMeResponse>(fetcher, '/auth/me', accessToken),
			backendFetch<TenantAccessResponse[]>(fetcher, '/auth/me/tenants', accessToken)
		]);
		return buildSession(accessToken, refreshToken, cookies, user, memberships);
	} catch {
		const refreshed = await refreshSessionToken(fetcher, cookies, refreshToken);
		if (!refreshed) {
			clearAuthCookies(cookies);
			throw redirect(303, '/login?expired=1');
		}

		if (!refreshed.access_token) {
			clearAuthCookies(cookies);
			throw redirect(303, '/login?expired=1');
		}

		accessToken = refreshed.access_token;
		const [user, memberships] = await Promise.all([
			backendFetch<AuthMeResponse>(fetcher, '/auth/me', accessToken),
			backendFetch<TenantAccessResponse[]>(fetcher, '/auth/me/tenants', accessToken)
		]);
		return buildSession(accessToken, refreshed.refresh_token, cookies, user, memberships);
	}
}

function buildSession(
	accessToken: string,
	refreshToken: string | null,
	cookies: Cookies,
	user: AuthMeResponse,
	memberships: TenantAccessResponse[]
): ServerAuthSession {
	const activeTenantId = cookies.get(ACTIVE_TENANT_COOKIE);
	const activeTenant = activeTenantId
		? memberships.find((membership) => membership.tenant_id === activeTenantId) ?? null
		: null;

	if (activeTenantId && !activeTenant) {
		cookies.delete(ACTIVE_TENANT_COOKIE, COOKIE_OPTIONS);
	}

	return {
		accessToken,
		refreshToken,
		user,
		memberships,
		activeTenant
	};
}

export function setActiveTenantCookie(cookies: Cookies, tenantId: string) {
	cookies.set(ACTIVE_TENANT_COOKIE, tenantId, {
		...COOKIE_OPTIONS,
		maxAge: 60 * 60 * 24 * 365
	});
}
