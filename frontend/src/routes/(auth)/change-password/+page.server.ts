import { requireAuthSession } from '$lib/server/auth';

export const load = async ({ fetch, cookies }) => {
	const session = await requireAuthSession(fetch, cookies);

	return {
		user: session.user,
		memberships: session.memberships,
		accessToken: session.accessToken,
		refreshToken: session.refreshToken
	};
};
