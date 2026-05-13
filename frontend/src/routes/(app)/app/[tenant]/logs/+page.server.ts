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

	const documents: DocumentResponse[] = [];
	for (const col of collections) {
		try {
			const docs = await tenantBackendRequest<DocumentResponse[]>(
				fetch,
				`/tenant/collections/${col.id}/documents`,
				session
			);
			documents.push(...docs);
		} catch {
			// ignore if collection docs can't be loaded
		}
	}

	return { logs, instances, collections, documents };
};
