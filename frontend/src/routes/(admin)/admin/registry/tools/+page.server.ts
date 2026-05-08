import { superadminBackendRequest } from '$lib/server/api';
import type { ToolDefinitionResponse } from '$lib/api/types';

export const load = async ({ fetch, parent }) => {
	const session = await parent();
	const tools = await superadminBackendRequest<ToolDefinitionResponse[]>(
		fetch,
		'/superadmin/registry/tools',
		session
	);
	return { tools };
};
