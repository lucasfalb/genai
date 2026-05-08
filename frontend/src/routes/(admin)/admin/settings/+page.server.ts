import { superadminBackendRequest } from '$lib/server/api';
import type { SystemSettingsResponse } from '$lib/api/types';

export const load = async ({ fetch, parent }) => {
	const session = await parent();
	const settings = await superadminBackendRequest<SystemSettingsResponse>(
		fetch,
		'/superadmin/system-settings',
		session
	);
	return { settings };
};
