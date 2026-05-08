import { tenantBackendRequest } from '$lib/server/api';
import type { CollectionResponse } from '$lib/api/types';

export const load = async ({ fetch, parent }) => {
	const session = await parent();
	const collections = await tenantBackendRequest<CollectionResponse[]>(
		fetch,
		'/tenant/collections',
		session
	);

	return { collections };
};
