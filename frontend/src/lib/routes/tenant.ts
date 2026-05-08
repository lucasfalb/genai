import type { TenantAccessResponse } from '$lib/api/types';

export function tenantBasePath(tenant: Pick<TenantAccessResponse, 'tenant_slug' | 'tenant_id'>): string {
	return `/app/${encodeURIComponent(tenant.tenant_slug || tenant.tenant_id)}`;
}

export function tenantPath(
	tenant: Pick<TenantAccessResponse, 'tenant_slug' | 'tenant_id'>,
	path = ''
): string {
	const normalized = path.startsWith('/') ? path : `/${path}`;
	return `${tenantBasePath(tenant)}${normalized === '/' ? '' : normalized}`;
}

export function tenantBaseFromPath(pathname: string): string {
	const [, appSegment, tenant] = pathname.split('/');
	if (appSegment === 'app' && tenant) {
		return `/app/${encodeURIComponent(tenant)}`;
	}
	return '/app';
}
