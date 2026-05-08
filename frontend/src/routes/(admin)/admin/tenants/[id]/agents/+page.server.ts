import { superadminBackendRequest } from '$lib/server/api';
import type { SuperadminAgentInstanceResponse } from '$lib/api/types';

export const load = async ({ fetch, params, parent }) => {
	const { accessToken } = await parent();
	const instances = await superadminBackendRequest<SuperadminAgentInstanceResponse[]>(
		fetch,
		`/superadmin/tenants/${params.id}/instances`,
		{ accessToken }
	);
	return { instances };
};
