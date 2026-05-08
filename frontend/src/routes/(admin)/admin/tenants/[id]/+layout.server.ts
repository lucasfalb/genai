import { redirect } from '@sveltejs/kit';
import { superadminBackendRequest } from '$lib/server/api';
import type { SuperadminTenantResponse } from '$lib/api/types';

export const load = async ({ fetch, params, parent }) => {
	const { accessToken } = await parent();
	try {
		const tenant = await superadminBackendRequest<SuperadminTenantResponse>(
			fetch,
			`/superadmin/tenants/${params.id}`,
			{ accessToken }
		);
		return { tenant };
	} catch {
		throw redirect(303, '/admin/tenants');
	}
};
