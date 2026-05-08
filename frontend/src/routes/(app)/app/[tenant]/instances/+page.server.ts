import { tenantBackendRequest } from '$lib/server/api';
import type { AgentInstanceResponse } from '$lib/api/types';

export const load = async ({ fetch, parent }) => {
	const session = await parent();
	const instances = await tenantBackendRequest<AgentInstanceResponse[]>(
		fetch,
		'/tenant/instances',
		session
	);

	return { instances };
};
