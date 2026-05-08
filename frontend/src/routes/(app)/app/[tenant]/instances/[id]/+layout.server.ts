import { tenantBackendRequest } from '$lib/server/api';
import type {
	AgentInstanceResponse,
	AgentPromptConfigResponse,
	ToolMetadataResponse
} from '$lib/api/types';

export const load = async ({ fetch, parent, params }) => {
	const session = await parent();
	const [instance, promptConfig, registryMetadata] = await Promise.all([
		tenantBackendRequest<AgentInstanceResponse>(fetch, `/tenant/instances/${params.id}`, session),
		tenantBackendRequest<AgentPromptConfigResponse>(
			fetch,
			`/tenant/instances/${params.id}/prompt-config`,
			session
		),
		tenantBackendRequest<ToolMetadataResponse>(
			fetch,
			`/registry/instances/${params.id}/metadata`,
			session
		).catch(() => ({
			tenant_id: session.activeTenant?.tenant_id ?? '',
			instance_id: params.id,
			skills: [],
			tools: []
		}))
	]);

	return { instance, promptConfig, registryMetadata };
};
