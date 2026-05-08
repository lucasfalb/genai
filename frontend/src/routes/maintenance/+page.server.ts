import { redirect } from '@sveltejs/kit';

export const load = async ({ parent }) => {
	const { publicSettings } = await parent();
	if (!publicSettings.maintenance_mode) {
		throw redirect(303, '/');
	}
	return { publicSettings };
};
