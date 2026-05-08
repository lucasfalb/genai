import { api } from '$lib/api/client';
import type {
	AgentInstanceResponse,
	AgentInstanceCreateRequest,
	AgentInstanceUpdateRequest,
	AgentPromptConfigResponse,
	AgentPromptConfigRequest
} from '$lib/api/types';

export const instancesApi = {
	list: () => api.get<AgentInstanceResponse[]>('/tenant/instances'),

	create: (body: AgentInstanceCreateRequest) =>
		api.post<AgentInstanceResponse>('/tenant/instances', body),

	get: (id: string) => api.get<AgentInstanceResponse>(`/tenant/instances/${id}`),

	update: (id: string, body: AgentInstanceUpdateRequest) =>
		api.patch<AgentInstanceResponse>(`/tenant/instances/${id}`, body),

	delete: (id: string) => api.del<void>(`/tenant/instances/${id}`),

	getPromptConfig: (id: string) =>
		api.get<AgentPromptConfigResponse>(`/tenant/instances/${id}/prompt-config`),

	savePromptConfig: (id: string, body: AgentPromptConfigRequest) =>
		api.put<AgentPromptConfigResponse>(`/tenant/instances/${id}/prompt-config`, body)
};
