import { redirect } from '@sveltejs/kit';

export const load = ({ url }) => {
	const token = url.searchParams.get('token');
	throw redirect(303, token ? `/invite?token=${encodeURIComponent(token)}` : '/invite');
};
