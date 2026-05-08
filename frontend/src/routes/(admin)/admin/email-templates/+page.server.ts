import { superadminBackendRequest } from '$lib/server/api';
import type { EmailTemplateResponse } from '$lib/api/types';

export const load = async ({ fetch, parent }) => {
	const session = await parent();
	const templates = await superadminBackendRequest<EmailTemplateResponse[]>(
		fetch,
		'/superadmin/email-templates',
		session
	);
	return { templates };
};
