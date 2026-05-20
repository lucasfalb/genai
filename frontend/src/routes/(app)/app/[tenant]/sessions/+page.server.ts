import { tenantBackendRequest } from '$lib/server/api';
import type { AgentInstanceResponse, SessionListItem } from '$lib/api/types';
import type { PageServerLoad } from './$types';

const PAGE_SIZE = 50;

export const load: PageServerLoad = async ({ fetch, parent }) => {
	const session = await parent();
	const query = new URLSearchParams({ limit: String(PAGE_SIZE) });

	const [sessions, instances] = await Promise.all([
		tenantBackendRequest<SessionListItem[]>(fetch, `/tenant/sessions?${query}`, session),
		tenantBackendRequest<AgentInstanceResponse[]>(fetch, '/tenant/instances', session)
	]);

	return {
		sessions,
		instances,
		hasMore: sessions.length >= PAGE_SIZE
	};
};
