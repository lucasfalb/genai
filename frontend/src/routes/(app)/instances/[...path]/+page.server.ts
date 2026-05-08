import { redirectToTenantPath } from '$lib/server/tenant-route';

export const load = async ({ parent, params }) => {
	const session = await parent();
	redirectToTenantPath(303, session.activeTenant, `/instances/${params.path}`);
};
