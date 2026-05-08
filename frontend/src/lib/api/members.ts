import { api } from '$lib/api/client';
import type { TenantMemberResponse, TenantMemberUpdateRequest } from '$lib/api/types';

export const membersApi = {
	list: () => api.get<TenantMemberResponse[]>('/tenant/members'),

	update: (userId: string, body: TenantMemberUpdateRequest) =>
		api.patch<TenantMemberResponse>(`/tenant/members/${userId}`, body),

	remove: (userId: string) => api.del(`/tenant/members/${userId}`)
};
