import { tenantBackendRequest } from '$lib/server/api';
import type { AgentInstanceResponse, RunTraceListItem } from '$lib/api/types';
import type { PageServerLoad } from './$types';

const PAGE_SIZE = 20;

export const load: PageServerLoad = async ({ fetch, parent }) => {
	const session = await parent();
	const query = new URLSearchParams({ limit: String(PAGE_SIZE) });

	const [runs, instances] = await Promise.all([
		tenantBackendRequest<RunTraceListItem[]>(fetch, `/agent/runs?${query}`, session),
		tenantBackendRequest<AgentInstanceResponse[]>(fetch, '/tenant/instances', session)
	]);

	return {
		runs,
		instances,
		hasMore: runs.length >= PAGE_SIZE
	};
};
