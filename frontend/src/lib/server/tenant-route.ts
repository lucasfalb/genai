import { redirect } from '@sveltejs/kit';
import type { TenantAccessResponse } from '$lib/api/types';
import { tenantPath } from '$lib/routes/tenant';

export function redirectToTenantPath(
	status: 303 | 307,
	activeTenant: TenantAccessResponse,
	path = '/dashboard'
): never {
	throw redirect(status, tenantPath(activeTenant, path));
}
