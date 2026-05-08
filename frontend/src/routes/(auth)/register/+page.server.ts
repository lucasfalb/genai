import { redirect } from '@sveltejs/kit';

export const load = async ({ parent }) => {
	const { publicSettings } = await parent();
	if (!publicSettings.registration_enabled) {
		throw redirect(303, '/login');
	}
	return {};
};
