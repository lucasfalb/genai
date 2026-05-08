import { tenantBackendRequest } from '$lib/server/api';
import type { CollectionResponse, DocumentResponse } from '$lib/api/types';

export const load = async ({ fetch, params, parent }) => {
	const session = await parent();
	const [collection, documents] = await Promise.all([
		tenantBackendRequest<CollectionResponse>(
			fetch,
			`/tenant/collections/${params.id}`,
			session
		),
		tenantBackendRequest<DocumentResponse[]>(
			fetch,
			`/tenant/collections/${params.id}/documents`,
			session
		).catch(() => [] as DocumentResponse[])
	]);

	return { collection, documents };
};
