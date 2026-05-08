export const load = async ({ parent }) => {
	const { publicSettings } = await parent();
	return { publicSettings };
};
