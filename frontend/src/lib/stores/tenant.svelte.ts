import { browser } from '$app/environment';
import type { TenantAccessResponse } from '$lib/api/types';

const COOKIE_TENANT = 'genai_tenant_id';
const COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

let activeTenantId = $state<string | null>(null);
let activeTenantSlug = $state<string | null>(null);
let activeTenantName = $state<string | null>(null);
let role = $state<string | null>(null);

function setActiveTenant(tenant: TenantAccessResponse) {
	activeTenantId = tenant.tenant_id;
	activeTenantSlug = tenant.tenant_slug;
	activeTenantName = tenant.tenant_name;
	role = tenant.role;
	if (browser) {
		document.cookie = `${COOKIE_TENANT}=${encodeURIComponent(tenant.tenant_id)}; path=/; max-age=${COOKIE_MAX_AGE}; samesite=lax`;
	}
}

function clearTenant() {
	activeTenantId = null;
	activeTenantSlug = null;
	activeTenantName = null;
	role = null;
	if (browser) {
		document.cookie = `${COOKIE_TENANT}=; path=/; max-age=0; samesite=lax`;
	}
}

export const tenantStore = {
	get activeTenantId() {
		return activeTenantId;
	},
	get activeTenantSlug() {
		return activeTenantSlug;
	},
	get activeTenantName() {
		return activeTenantName;
	},
	get role() {
		return role;
	},
	setActiveTenant,
	clearTenant
};
