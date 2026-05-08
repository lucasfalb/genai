import { browser } from '$app/environment';
import type { TenantAccessResponse } from '$lib/api/types';

const LS_TENANT = 'genai_tenant_id';
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
		localStorage.setItem(LS_TENANT, tenant.tenant_id);
		document.cookie = `${LS_TENANT}=${encodeURIComponent(tenant.tenant_id)}; path=/; max-age=${COOKIE_MAX_AGE}; samesite=lax`;
	}
}

function clearTenant() {
	activeTenantId = null;
	activeTenantSlug = null;
	activeTenantName = null;
	role = null;
	if (browser) {
		localStorage.removeItem(LS_TENANT);
		document.cookie = `${LS_TENANT}=; path=/; max-age=0; samesite=lax`;
	}
}

function loadFromLocalStorage(memberships: TenantAccessResponse[]) {
	if (!browser) return;
	const stored = localStorage.getItem(LS_TENANT);
	if (!stored) return;
	const match = memberships.find((m) => m.tenant_id === stored);
	if (match) setActiveTenant(match);
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
	clearTenant,
	loadFromLocalStorage
};
