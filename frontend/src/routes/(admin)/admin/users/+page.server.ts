import { superadminBackendRequest } from '$lib/server/api';
import type { SuperadminUserResponse } from '$lib/api/types';

export const load = async ({ fetch, parent }) => {
	const session = await parent();
	const users = await superadminBackendRequest<SuperadminUserResponse[]>(
		fetch,
		'/superadmin/users',
		session
	);
	return { users };
};
