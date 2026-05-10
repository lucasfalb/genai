import { api } from '$lib/api/client';
import type { TenantProvidersResponse, ProviderConfigRequest, ProviderModelsResponse } from '$lib/api/types';

export const aiSettingsApi = {
	get: () => api.get<TenantProvidersResponse>('/tenant/settings'),
	save: (body: ProviderConfigRequest) => api.post<TenantProvidersResponse>('/tenant/settings', body),
	delete: (providerName: string) => api.del<void>(`/tenant/settings?provider_name=${providerName}`),
	getModels: (provider: string) => api.get<ProviderModelsResponse>(`/tenant/settings/${provider}/models`)
};
