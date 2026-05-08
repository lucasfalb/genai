import { redirect } from '@sveltejs/kit';
import { requireAuthSession, setActiveTenantCookie } from '$lib/server/auth';
import { superadminBackendRequest } from '$lib/server/api';
import { tenantPath } from '$lib/routes/tenant';
import type { SuperadminTenantResponse, TenantAccessResponse } from '$lib/api/types';

export const load = async ({ fetch, cookies }) => {
	const session = await requireAuthSession(fetch, cookies);
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

	if (memberships.length === 0) {
		if (session.user.is_superadmin) {
			throw redirect(303, '/admin');
		}
		throw redirect(303, '/awaiting');
	}

	if (memberships.length === 1) {
		setActiveTenantCookie(cookies, memberships[0].tenant_id);
		throw redirect(303, tenantPath(memberships[0], '/dashboard'));
	}

	return {
		user: session.user,
		memberships,
		accessToken: session.accessToken,
		refreshToken: session.refreshToken
	};
};
