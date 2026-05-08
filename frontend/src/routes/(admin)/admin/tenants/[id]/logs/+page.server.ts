import { superadminBackendRequest } from '$lib/server/api';
import type { SuperadminAuditLogResponse } from '$lib/api/types';

export const load = async ({ fetch, params, parent }) => {
	const { accessToken } = await parent();
	const logs = await superadminBackendRequest<SuperadminAuditLogResponse[]>(
		fetch,
		`/superadmin/tenants/${params.id}/audit`,
		{ accessToken }
	);
	return { logs };
};
