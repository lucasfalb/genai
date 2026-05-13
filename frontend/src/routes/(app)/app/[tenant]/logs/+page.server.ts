import { tenantBackendRequest } from '$lib/server/api';
import type { SuperadminAuditLogResponse, AgentInstanceResponse, CollectionResponse, DocumentResponse } from '$lib/api/types';

export const load = async ({ fetch, parent, url }) => {
	const session = await parent();

	const auditParams = new URLSearchParams();
	const startedAt = url.searchParams.get('started_at');
	const endedAt = url.searchParams.get('ended_at');
	const action = url.searchParams.get('action');
	const resource = url.searchParams.get('resource');
	if (startedAt) auditParams.set('started_at', startedAt);
	if (endedAt) auditParams.set('ended_at', endedAt);
	if (action) auditParams.set('action', action);
	if (resource) auditParams.set('resource', resource);

	const auditQuery = auditParams.toString();
	const auditEndpoint = `/tenant/audit${auditQuery ? `?${auditQuery}` : ''}`;

	const [logs, instances, collections] = await Promise.all([
		tenantBackendRequest<SuperadminAuditLogResponse[]>(fetch, auditEndpoint, session),
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
