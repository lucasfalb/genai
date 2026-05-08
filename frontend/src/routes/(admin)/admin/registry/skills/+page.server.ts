import { superadminBackendRequest } from '$lib/server/api';
import type { SkillDefinitionResponse } from '$lib/api/types';

export const load = async ({ fetch, parent }) => {
	const session = await parent();
	const skills = await superadminBackendRequest<SkillDefinitionResponse[]>(
		fetch,
		'/superadmin/registry/skills',
		session
	);
	return { skills };
};
