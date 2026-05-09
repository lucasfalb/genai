import { redirect } from '@sveltejs/kit';
import { requireAuthSession, setActiveTenantCookie } from '$lib/server/auth';
import { superadminBackendRequest } from '$lib/server/api';
import type { SuperadminTenantResponse, TenantAccessResponse } from '$lib/api/types';

export const load = async ({ fetch, cookies, params, url, parent }) => {
	const [{ publicSettings }, session] = await Promise.all([
		parent(),
		requireAuthSession(fetch, cookies)
	]);
	console.log('[app layout] requireAuthSession resolved, activeTenant:', session.activeTenant?.tenant_id, session.activeTenant?.tenant_slug);
	console.log('[app layout] memberships count:', session.memberships.length);
	console.log('[app layout] cookies tenant_id:', cookies.get('genai_tenant_id'));
	let memberships = session.memberships;

	if (session.user.is_superadmin) {
		console.log('[app layout] user is superadmin, loading all tenants');
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

	// Try to resolve activeTenant from session first (regular user path),
	// then from cookie directly (superadmin path — session.activeTenant
	// may be null because memberships were empty during buildSession).
	let activeTenant = session.activeTenant
		? memberships.find((m) => m.tenant_id === session.activeTenant!.tenant_id) ?? null
		: null;
	if (!activeTenant) {
		const cookieTid = cookies.get('genai_tenant_id');
		console.log('[app layout] retry from cookie:', cookieTid);
		if (cookieTid) {
			activeTenant = memberships.find((m) => m.tenant_id === cookieTid) ?? null;
		}
	}
	console.log('[app layout] activeTenant after lookup:', activeTenant?.tenant_id, activeTenant?.tenant_slug);
	if (!activeTenant && memberships.length === 1) {
		console.log('[app layout] auto-selecting single membership');
		activeTenant = memberships[0];
		setActiveTenantCookie(cookies, activeTenant.tenant_id);
	}

	if (!activeTenant) {
		console.log('[app layout] no active tenant, redirecting to /tenant-select');
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
