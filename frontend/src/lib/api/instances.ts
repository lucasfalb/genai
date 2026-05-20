import { api } from '$lib/api/client';
import type {
	AgentInstanceResponse,
	AgentInstanceCreateRequest,
	AgentInstanceUpdateRequest,
	AgentLinkCreateRequest,
	AgentLinkResponse,
	AgentLinkUpdateRequest,
	AgentPromptConfigResponse,
	AgentPromptConfigRequest,
	VersionEntry,
	ChannelConfigResponse,
	WebWidgetConfig
} from '$lib/api/types';

export const instancesApi = {
	list: () => api.get<AgentInstanceResponse[]>('/tenant/instances'),

	create: (body: AgentInstanceCreateRequest) =>
		api.post<AgentInstanceResponse>('/tenant/instances', body),

	get: (id: string) => api.get<AgentInstanceResponse>(`/tenant/instances/${id}`),

	update: (id: string, body: AgentInstanceUpdateRequest) =>
		api.patch<AgentInstanceResponse>(`/tenant/instances/${id}`, body),

	delete: (id: string) => api.del<void>(`/tenant/instances/${id}`),

	listLinks: (id: string) => api.get<AgentLinkResponse[]>(`/tenant/instances/${id}/links`),

	createLink: (id: string, body: AgentLinkCreateRequest) =>
		api.post<AgentLinkResponse>(`/tenant/instances/${id}/links`, body),

	updateLink: (id: string, linkId: string, body: AgentLinkUpdateRequest) =>
		api.patch<AgentLinkResponse>(`/tenant/instances/${id}/links/${linkId}`, body),

	deleteLink: (id: string, linkId: string) =>
		api.del<void>(`/tenant/instances/${id}/links/${linkId}`),

	getPromptConfig: (id: string) =>
		api.get<AgentPromptConfigResponse>(`/tenant/instances/${id}/prompt-config`),

	savePromptConfig: (id: string, body: AgentPromptConfigRequest) =>
		api.put<AgentPromptConfigResponse>(`/tenant/instances/${id}/prompt-config`, body),

	getVersions: (id: string) => api.get<VersionEntry[]>(`/tenant/instances/${id}/versions`),

	getChannelConfig: (id: string, channel: string) =>
		api.get<ChannelConfigResponse>(`/tenant/instances/${id}/channels/${channel}`),

	updateChannelConfig: (
		id: string,
		channel: string,
		body: { config: WebWidgetConfig; allowed_origins: string[]; is_active?: boolean | null }
	) => api.put<ChannelConfigResponse>(`/tenant/instances/${id}/channels/${channel}`, body),

	activateChannel: (id: string, channel: string) =>
		api.post<ChannelConfigResponse>(`/tenant/instances/${id}/channels/${channel}/activate`, {}),

	deactivateChannel: (id: string, channel: string) =>
		api.post<ChannelConfigResponse>(`/tenant/instances/${id}/channels/${channel}/deactivate`, {}),

	uploadChannelImage: (id: string, file: File): Promise<{ url: string }> => {
		const form = new FormData();
		form.append('file', file);
		return api.upload<{ url: string }>(`/tenant/instances/${id}/channels/widget/upload-image`, form);
	}
};
