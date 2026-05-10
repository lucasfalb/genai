import { isHttpError } from '@sveltejs/kit';
import { tenantBackendRequest } from '$lib/server/api';
import type { TenantProvidersResponse } from '$lib/api/types';

export const load = async ({ fetch, parent }) => {
	const session = await parent();
	let config: TenantProvidersResponse | null = null;
	try {
		config = await tenantBackendRequest<TenantProvidersResponse>(fetch, '/tenant/settings', session);
	} catch (err) {
		if (!isHttpError(err) || err.status !== 404) throw err;
	}
	return { config };
};
