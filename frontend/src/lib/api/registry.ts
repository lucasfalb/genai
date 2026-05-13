import { api } from '$lib/api/client';
import type {
	ActivationRequest,
	CredentialRequest,
	CredentialResponse,
	RegistryCatalogResponse,
	SkillActivationResponse,
	ToolActivationResponse,
	ToolTestRequest,
	ToolTestResponse,
	ToolMetadataResponse
} from '$lib/api/types';

export const registryApi = {
	getCatalog: () => api.get<RegistryCatalogResponse>('/registry/catalog'),

	getCredentials: () => api.get<CredentialResponse[]>('/registry/credentials'),

	saveCredential: (skillSlug: string, body: CredentialRequest) =>
		api.put<CredentialResponse>(`/registry/credentials/${skillSlug}`, body),

	getMetadata: (instanceId: string) =>
		api.get<ToolMetadataResponse>(`/registry/instances/${instanceId}/metadata`),

	activateSkill: (instanceId: string, skillSlug: string, body: ActivationRequest) =>
		api.put<SkillActivationResponse>(`/registry/instances/${instanceId}/skills/${skillSlug}`, body),

	activateToolItem: (instanceId: string, toolSlug: string, body: ActivationRequest) =>
		api.put<ToolActivationResponse>(`/registry/instances/${instanceId}/tools/${toolSlug}`, body),

	testTool: (instanceId: string, toolSlug: string, body: ToolTestRequest) =>
		api.post<ToolTestResponse>(`/registry/instances/${instanceId}/tools/${toolSlug}/test`, body),

	removeSkill: (instanceId: string, skillSlug: string) =>
		api.del<{ message: string }>(`/registry/instances/${instanceId}/skills/${skillSlug}`),

	removeTool: (instanceId: string, toolSlug: string) =>
		api.del<{ message: string }>(`/registry/instances/${instanceId}/tools/${toolSlug}`)
};
