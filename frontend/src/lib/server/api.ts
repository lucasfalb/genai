import { PUBLIC_API_BASE_URL } from '$env/static/public';
import { error } from '@sveltejs/kit';

interface ApiSuccess<T> {
	status: 'success';
	data: T;
}

interface ApiFailure {
	status: 'error';
	error: {
		code: string;
		message: string;
	};
}

export async function tenantBackendRequest<T>(
	fetcher: typeof fetch,
	path: string,
	session: {
		accessToken: string;
		activeTenant: { tenant_id: string } | null;
	},
	init: RequestInit = {}
): Promise<T> {
	if (!session.activeTenant) {
		throw error(400, 'Tenant context is required.');
	}

	const response = await fetcher(`${PUBLIC_API_BASE_URL}${path}`, {
		...init,
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${session.accessToken}`,
			'X-Tenant-ID': session.activeTenant.tenant_id,
			...init.headers
		}
	});

	const payload = (await response.json().catch(() => null)) as ApiSuccess<T> | ApiFailure | null;

	if (!response.ok || !payload || payload.status === 'error') {
		const message =
			payload && payload.status === 'error'
				? payload.error.message
				: response.statusText || 'Backend request failed.';
		throw error(response.status || 500, message);
	}

	return payload.data;
}

export async function superadminBackendRequest<T>(
	fetcher: typeof fetch,
	path: string,
	session: { accessToken: string },
	init: RequestInit = {}
): Promise<T> {
	const response = await fetcher(`${PUBLIC_API_BASE_URL}${path}`, {
		...init,
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${session.accessToken}`,
			...init.headers
		}
	});

	const payload = (await response.json().catch(() => null)) as ApiSuccess<T> | ApiFailure | null;

	if (!response.ok || !payload || payload.status === 'error') {
		const message =
			payload && payload.status === 'error'
				? payload.error.message
				: response.statusText || 'Backend request failed.';
		throw error(response.status || 500, message);
	}

	return payload.data;
}
