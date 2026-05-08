import { tenantBackendRequest } from '$lib/server/api';
import type { CredentialResponse } from '$lib/api/types';

export const load = async ({ fetch, parent }) => {
	const session = await parent();
	const credentials = await tenantBackendRequest<CredentialResponse[]>(
		fetch,
		'/registry/credentials',
		session
	).catch(() => []);

	return { credentials };
};
