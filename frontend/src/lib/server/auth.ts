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
	try {
		cookies.delete(AUTH_ACCESS_COOKIE, COOKIE_OPTIONS);
		cookies.delete(AUTH_REFRESH_COOKIE, COOKIE_OPTIONS);
		cookies.delete(ACTIVE_TENANT_COOKIE, COOKIE_OPTIONS);
	} catch {
		// cookies may be locked if the response has already been generated
	}
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

	console.log('[requireAuthSession] accessToken:', accessToken?.slice(0, 10) + '...');
	console.log('[requireAuthSession] refreshToken:', refreshToken?.slice(0, 10) + '...');
	console.log('[requireAuthSession] genai_tenant_id cookie:', cookies.get(ACTIVE_TENANT_COOKIE));

	if (!accessToken) {
		console.log('[requireAuthSession] no access token, redirecting to /login');
		throw redirect(303, '/login');
	}

	try {
		const [user, memberships] = await Promise.all([
			backendFetch<AuthMeResponse>(fetcher, '/auth/me', accessToken),
			backendFetch<TenantAccessResponse[]>(fetcher, '/auth/me/tenants', accessToken)
		]);
		console.log('[requireAuthSession] backend fetch success, memberships:', memberships.length);
		return buildSession(accessToken, refreshToken, cookies, user, memberships);
	} catch {
		console.log('[requireAuthSession] backend fetch failed, trying refresh');
		const refreshed = await refreshSessionToken(fetcher, cookies, refreshToken);
		if (!refreshed) {
			console.log('[requireAuthSession] refresh failed');
			clearAuthCookies(cookies);
			throw redirect(303, '/login?expired=1');
		}

		if (!refreshed.access_token) {
			console.log('[requireAuthSession] refresh returned no access_token');
			clearAuthCookies(cookies);
			throw redirect(303, '/login?expired=1');
		}

		console.log('[requireAuthSession] refresh succeeded');
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
	console.log('[buildSession] activeTenantId from cookie:', activeTenantId);
	let activeTenant: TenantAccessResponse | null = null;
	if (activeTenantId) {
		activeTenant = memberships.find((m) => m.tenant_id === activeTenantId) ?? null;
	}
	console.log('[buildSession] matched activeTenant:', activeTenant?.tenant_id, activeTenant?.tenant_slug);

	// Only delete cookie when memberships exist and none matches.
	// Superadmins have empty memberships here — their tenant list is fetched later.
	if (activeTenantId && !activeTenant && memberships.length > 0) {
		console.log('[buildSession] activeTenantId from cookie not found in memberships, deleting cookie');
		try {
			cookies.delete(ACTIVE_TENANT_COOKIE, COOKIE_OPTIONS);
		} catch {
			// cookies may be locked if the response has already been generated
		}
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
