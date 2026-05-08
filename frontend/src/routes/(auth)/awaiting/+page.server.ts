import { redirect } from '@sveltejs/kit';
import { requireAuthSession, setActiveTenantCookie } from '$lib/server/auth';
import { tenantPath } from '$lib/routes/tenant';

export const load = async ({ fetch, cookies }) => {
	let session;
	try {
		session = await requireAuthSession(fetch, cookies);
	} catch {
		return {
			user: null,
			accessToken: null,
			refreshToken: null
		};
	}

	if (session.user.is_superadmin && session.memberships.length === 0) {
		throw redirect(303, '/admin');
	}

	if (session.memberships.length === 1) {
		setActiveTenantCookie(cookies, session.memberships[0].tenant_id);
		throw redirect(303, tenantPath(session.memberships[0], '/dashboard'));
	}

	if (session.memberships.length > 1) {
		throw redirect(303, '/tenant-select');
	}

	return {
		user: session.user,
		accessToken: session.accessToken,
		refreshToken: session.refreshToken
	};
};
