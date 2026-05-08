import { api } from '$lib/api/client';
import type { TenantAIConfigResponse, TenantAIConfigRequest } from '$lib/api/types';

export const aiSettingsApi = {
	get: () => api.get<TenantAIConfigResponse>('/tenant/settings/ai'),
	save: (body: TenantAIConfigRequest) => api.put<TenantAIConfigResponse>('/tenant/settings/ai', body),
	delete: () => api.del<void>('/tenant/settings/ai')
};
