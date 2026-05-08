import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError } from './client';
import { authStore } from '$lib/stores/auth.svelte';
import { tenantStore } from '$lib/stores/tenant.svelte';

const ok = <T>(data: T, init: ResponseInit = {}) =>
	new Response(JSON.stringify({ status: 'success', data }), {
		status: init.status ?? 200,
		headers: { 'Content-Type': 'application/json' }
	});

const err = (status: number, code: string, message: string) =>
	new Response(JSON.stringify({ status: 'error', error: { code, message } }), {
		status,
		headers: { 'Content-Type': 'application/json' }
	});

describe('api client', () => {
	beforeEach(() => {
		authStore.clearAuth();
		tenantStore.clearTenant();
		vi.restoreAllMocks();
	});

	it('injects Authorization and X-Tenant-ID headers', async () => {
		authStore.setTokens('access-token', 'refresh-token');
		tenantStore.setActiveTenant({
			tenant_id: 'tenant-1',
			tenant_slug: 'tenant',
			tenant_name: 'Tenant',
			role: 'admin',
			status: 'active'
		});
		const fetchMock = vi.fn().mockResolvedValue(ok({ id: '123' }));
		vi.stubGlobal('fetch', fetchMock);

		await api.get<{ id: string }>('/example');

		const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
		expect(init.headers).toMatchObject({
			Authorization: 'Bearer access-token',
			'X-Tenant-ID': 'tenant-1'
		});
	});

	it('retries once after a successful refresh on 401', async () => {
		authStore.setTokens('expired-access', 'refresh-token');
		const fetchMock = vi
			.fn()
			.mockResolvedValueOnce(err(401, 'UNAUTHORIZED', 'Unauthorized'))
			.mockResolvedValueOnce(
				ok({
					access_token: 'new-access',
					refresh_token: 'new-refresh'
				})
			)
			.mockResolvedValueOnce(ok({ value: 'done' }));
		vi.stubGlobal('fetch', fetchMock);

		const result = await api.get<{ value: string }>('/protected');

		expect(result.value).toBe('done');
		expect(fetchMock).toHaveBeenCalledTimes(3);
		const [, retryInit] = fetchMock.mock.calls[2] as [string, RequestInit];
		expect(retryInit.headers).toMatchObject({ Authorization: 'Bearer new-access' });
	});

	it('clears auth and throws when refresh fails', async () => {
		authStore.setTokens('expired-access', 'refresh-token');
		const location = { href: '' };
		vi.stubGlobal('window', { location });
		vi.stubGlobal(
			'fetch',
			vi
				.fn()
				.mockResolvedValueOnce(err(401, 'UNAUTHORIZED', 'Unauthorized'))
				.mockResolvedValueOnce(err(401, 'INVALID_REFRESH_TOKEN', 'Invalid refresh token'))
		);

		await expect(api.get('/protected')).rejects.toThrow(ApiError);

		expect(authStore.accessToken).toBeNull();
		expect(authStore.refreshToken).toBeNull();
		expect(location.href).toBe('/login');
	});

	it('throws ApiError with the backend error message and code', async () => {
		vi.stubGlobal('fetch', vi.fn().mockResolvedValue(err(409, 'EMAIL_ALREADY_REGISTERED', 'Email already registered')));

		await expect(api.post('/auth/register', {})).rejects.toMatchObject({
			status: 409,
			code: 'EMAIL_ALREADY_REGISTERED',
			message: 'Email already registered'
		});
	});

	it('can skip auth and tenant headers for public endpoints', async () => {
		authStore.setTokens('access-token', 'refresh-token');
		tenantStore.setActiveTenant({
			tenant_id: 'tenant-1',
			tenant_slug: 'tenant',
			tenant_name: 'Tenant',
			role: 'admin',
			status: 'active'
		});
		const fetchMock = vi.fn().mockResolvedValue(ok({ public: true }));
		vi.stubGlobal('fetch', fetchMock);

		await api.get('/system-settings/public', undefined, { skipAuth: true, skipTenant: true });

		const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
		expect(init.headers).not.toMatchObject({
			Authorization: expect.any(String),
			'X-Tenant-ID': expect.any(String)
		});
	});
});
