import { api } from '$lib/api/client';
import type {
	LoginRequest,
	RegisterRequest,
	LogoutRequest,
	RefreshRequest,
	AuthResponse,
	AuthMeResponse,
	TenantAccessResponse,
	AccountActivationRequest,
	AccountActivationConfirmRequest,
	PasswordForgotRequest,
	PasswordResetRequest,
	PasswordChangeRequest,
	PublicSystemSettingsResponse
} from '$lib/api/types';

export const authApi = {
	login: (body: LoginRequest) =>
		api.post<AuthResponse>('/auth/login', body, { skipAuth: true, skipTenant: true }),

	register: (body: RegisterRequest) =>
		api.post<void>('/auth/register', body, { skipAuth: true, skipTenant: true }),

	logout: (body: LogoutRequest) => api.post<void>('/auth/logout', body, { skipTenant: true }),

	refresh: (body: RefreshRequest) =>
		api.post<AuthResponse>('/auth/refresh', body, { skipAuth: true, skipTenant: true }),

	me: () => api.get<AuthMeResponse>('/auth/me', undefined, { skipTenant: true }),

	myTenants: () => api.get<TenantAccessResponse[]>('/auth/me/tenants', undefined, { skipTenant: true }),

	activationRequest: (body: AccountActivationRequest) =>
		api.post<void>('/auth/activation/request', body, { skipAuth: true, skipTenant: true }),

	activationConfirm: (body: AccountActivationConfirmRequest) =>
		api.post<void>('/auth/activation/confirm', body, { skipAuth: true, skipTenant: true }),

	passwordForgot: (body: PasswordForgotRequest) =>
		api.post<void>('/auth/password/forgot', body, { skipAuth: true, skipTenant: true }),

	passwordReset: (body: PasswordResetRequest) =>
		api.post<void>('/auth/password/reset', body, { skipAuth: true, skipTenant: true }),

	passwordChange: (body: PasswordChangeRequest) =>
		api.post<void>('/auth/password/change', body, { skipTenant: true }),

	publicSettings: () =>
		api.get<PublicSystemSettingsResponse>('/system-settings/public', undefined, {
			skipAuth: true,
			skipTenant: true
		})
};
