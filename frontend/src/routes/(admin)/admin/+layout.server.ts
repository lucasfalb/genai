import { redirect } from '@sveltejs/kit';
import { requireAuthSession } from '$lib/server/auth';

export const load = async ({ fetch, cookies }) => {
	const session = await requireAuthSession(fetch, cookies);

	if (!session.user.is_superadmin) {
		throw redirect(303, '/tenant-select');
	}

	return {
		user: session.user,
		accessToken: session.accessToken,
		refreshToken: session.refreshToken
	};
};
