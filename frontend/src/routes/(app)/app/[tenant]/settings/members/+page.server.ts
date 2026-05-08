import { tenantBackendRequest } from '$lib/server/api';
import type { TenantInvitationResponse, TenantMemberResponse } from '$lib/api/types';

export const load = async ({ fetch, parent }) => {
	const session = await parent();
	const [members, invitations] = await Promise.all([
		tenantBackendRequest<TenantMemberResponse[]>(fetch, '/tenant/members', session),
		tenantBackendRequest<TenantInvitationResponse[]>(fetch, '/tenant/invitations', session)
	]);

	return {
		members,
		invitations,
		currentUserId: session.user.id,
		currentRole: session.activeTenant?.role ?? null
	};
};
