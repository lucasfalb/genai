import { superadminBackendRequest } from '$lib/server/api';
import type { SuperadminUserResponse, TenantMemberResponse } from '$lib/api/types';

export const load = async ({ fetch, params, parent }) => {
	const { accessToken } = await parent();
	const session = { accessToken };
	const [members, users] = await Promise.all([
		superadminBackendRequest<TenantMemberResponse[]>(
			fetch,
			`/superadmin/tenants/${params.id}/members`,
			session
		),
		superadminBackendRequest<SuperadminUserResponse[]>(fetch, '/superadmin/users', session)
	]);
	return { members, users };
};
