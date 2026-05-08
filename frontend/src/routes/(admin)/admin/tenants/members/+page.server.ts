import { superadminBackendRequest } from '$lib/server/api';
import type { SuperadminTenantResponse } from '$lib/api/types';

export const load = async ({ fetch, parent }) => {
	const session = await parent();
	const tenants = await superadminBackendRequest<SuperadminTenantResponse[]>(
		fetch,
		'/superadmin/tenants',
		session
	);

	return { tenants };
};
