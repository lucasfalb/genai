import { isHttpError } from '@sveltejs/kit';
import { tenantBackendRequest } from '$lib/server/api';
import type { TenantAIConfigResponse } from '$lib/api/types';

export const load = async ({ fetch, parent }) => {
	const session = await parent();
	let config: TenantAIConfigResponse | null = null;
	try {
		config = await tenantBackendRequest<TenantAIConfigResponse>(fetch, '/tenant/settings/ai', session);
	} catch (err) {
		if (!isHttpError(err) || err.status !== 404) throw err;
	}
	return { config };
};
