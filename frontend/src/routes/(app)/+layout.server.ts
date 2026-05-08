import { redirect } from '@sveltejs/kit';
import { requireAuthSession, setActiveTenantCookie } from '$lib/server/auth';
import { superadminBackendRequest } from '$lib/server/api';
import type { SuperadminTenantResponse, TenantAccessResponse } from '$lib/api/types';

export const load = async ({ fetch, cookies, params, url, parent }) => {
	const [{ publicSettings }, session] = await Promise.all([
		parent(),
		requireAuthSession(fetch, cookies)
	]);
	let memberships = session.memberships;

	if (session.user.is_superadmin) {
		const tenants = await superadminBackendRequest<SuperadminTenantResponse[]>(
			fetch,
			'/superadmin/tenants',
			session
		);
		memberships = tenants.map((tenant): TenantAccessResponse => ({
			tenant_id: tenant.id,
			tenant_slug: tenant.slug,
			tenant_name: tenant.name,
			role: 'superadmin',
			status: tenant.status
		}));
	}

	if (publicSettings.maintenance_mode && !session.user.is_superadmin) {
		throw redirect(303, '/maintenance');
	}

	if (memberships.length === 0) {
		throw redirect(303, '/awaiting');
	}

	let activeTenant = session.activeTenant
		? memberships.find((membership) => membership.tenant_id === session.activeTenant?.tenant_id) ?? null
		: null;
	if (!activeTenant && memberships.length === 1) {
		activeTenant = memberships[0];
		setActiveTenantCookie(cookies, activeTenant.tenant_id);
	}

	if (!activeTenant) {
		throw redirect(303, '/tenant-select');
	}

	const routeTenant = params.tenant;
	if (routeTenant) {
		const routeMembership = memberships.find(
			(membership) =>
				membership.tenant_slug === routeTenant || membership.tenant_id === routeTenant
		);

		if (!routeMembership) {
			throw redirect(303, '/tenant-select');
		}

		if (activeTenant.tenant_id !== routeMembership.tenant_id) {
			setActiveTenantCookie(cookies, routeMembership.tenant_id);
			activeTenant = routeMembership;
		}

		if (routeTenant !== routeMembership.tenant_slug) {
			const normalizedPath = url.pathname.replace(
				`/app/${routeTenant}`,
				`/app/${routeMembership.tenant_slug}`
			);
			throw redirect(303, `${normalizedPath}${url.search}`);
		}
	}

	return {
		publicSettings,
		user: session.user,
		memberships,
		activeTenant,
		accessToken: session.accessToken,
		refreshToken: session.refreshToken
	};
};
