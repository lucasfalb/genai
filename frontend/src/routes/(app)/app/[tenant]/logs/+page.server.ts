import { tenantBackendRequest } from '$lib/server/api';
import type {
	SuperadminAuditLogResponse,
	AgentInstanceResponse,
	CollectionResponse,
	DocumentResponse
} from '$lib/api/types';

export const load = async ({ fetch, parent }) => {
	const session = await parent();

	const [logs, instances, collections] = await Promise.all([
		tenantBackendRequest<SuperadminAuditLogResponse[]>(fetch, '/tenant/audit', session),
		tenantBackendRequest<AgentInstanceResponse[]>(fetch, '/tenant/instances', session),
		tenantBackendRequest<CollectionResponse[]>(fetch, '/tenant/collections', session)
	]);

	const docResults = await Promise.all(
		collections.map((col) =>
			tenantBackendRequest<DocumentResponse[]>(
				fetch,
				`/tenant/collections/${col.id}/documents`,
				session
			).catch(() => [] as DocumentResponse[])
		)
	);
	const documents = docResults.flat();

	return { logs, instances, collections, documents };
};
