import { PUBLIC_API_BASE_URL } from '$env/static/public';
import type { PublicSystemSettingsResponse } from '$lib/api/types';

const DEFAULT_SETTINGS: PublicSystemSettingsResponse = {
	platform_name: 'GENAI',
	platform_public_url: '',
	platform_logo_url: '',
	maintenance_mode: false,
	registration_enabled: true,
	public_settings: {}
};

export const load = async ({ fetch }) => {
	try {
		const res = await fetch(`${PUBLIC_API_BASE_URL}/system-settings/public`);
		if (!res.ok) return { publicSettings: DEFAULT_SETTINGS };
		const payload = (await res.json()) as { status: 'success'; data: PublicSystemSettingsResponse };
		return { publicSettings: payload.data };
	} catch {
		return { publicSettings: DEFAULT_SETTINGS };
	}
};
