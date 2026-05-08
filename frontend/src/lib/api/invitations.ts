import { api } from '$lib/api/client';
import type {
	TenantInvitationValidateRequest,
	TenantInvitationPublicResponse,
	TenantInvitationAcceptRequest,
	TenantInvitationAcceptResponse,
	TenantInvitationResponse,
	TenantInvitationCreateRequest
} from '$lib/api/types';

export const invitationsPublicApi = {
	validate: (body: TenantInvitationValidateRequest) =>
		api.post<TenantInvitationPublicResponse>('/invitations/validate', body, {
			skipAuth: true,
			skipTenant: true
		}),

	accept: (body: TenantInvitationAcceptRequest) =>
		api.post<TenantInvitationAcceptResponse>('/invitations/accept', body, {
			skipAuth: true,
			skipTenant: true
		})
};

export const invitationsApi = {
	list: () => api.get<TenantInvitationResponse[]>('/tenant/invitations'),

	create: (body: TenantInvitationCreateRequest) =>
		api.post<TenantInvitationResponse>('/tenant/invitations', body),

	cancel: (id: string) => api.del(`/tenant/invitations/${id}`),

	resend: (id: string) => api.post<TenantInvitationResponse>(`/tenant/invitations/${id}/resend`)
};
