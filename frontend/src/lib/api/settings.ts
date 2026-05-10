import { api } from '$lib/api/client';
import type { TenantProvidersResponse, ProviderConfigRequest } from '$lib/api/types';

export const settingsApi = {
	getProviders: () => api.get<TenantProvidersResponse>('/tenant/settings'),
	upsertProvider: (body: ProviderConfigRequest) =>
		api.post<TenantProvidersResponse>('/tenant/settings/providers', body),
	deleteProvider: (providerName: string) => api.del<void>(`/tenant/settings/providers/${providerName}`)
};
