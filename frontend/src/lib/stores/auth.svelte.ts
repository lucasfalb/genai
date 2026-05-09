import { browser } from '$app/environment';
import type { AuthMeResponse, TenantAccessResponse } from '$lib/api/types';

const COOKIE_ACCESS = 'genai_access_token';
const COOKIE_REFRESH = 'genai_refresh_token';
const COOKIE_MAX_AGE = 60 * 60 * 24 * 30;

let user = $state<AuthMeResponse | null>(null);
let accessToken = $state<string | null>(null);
let refreshToken = $state<string | null>(null);
let memberships = $state<TenantAccessResponse[]>([]);

const isAuthenticated = $derived(accessToken !== null);

function setTokens(access: string, refresh: string) {
	accessToken = access;
	refreshToken = refresh;
	if (browser) {
		document.cookie = `${COOKIE_ACCESS}=${encodeURIComponent(access)}; path=/; max-age=${COOKIE_MAX_AGE}; samesite=lax`;
		document.cookie = `${COOKIE_REFRESH}=${encodeURIComponent(refresh)}; path=/; max-age=${COOKIE_MAX_AGE}; samesite=lax`;
	}
}

function clearAuth() {
	user = null;
	accessToken = null;
	refreshToken = null;
	memberships = [];
	if (browser) {
		document.cookie = `${COOKIE_ACCESS}=; path=/; max-age=0; samesite=lax`;
		document.cookie = `${COOKIE_REFRESH}=; path=/; max-age=0; samesite=lax`;
	}
}

export const authStore = {
	get user() {
		return user;
	},
	set user(v: AuthMeResponse | null) {
		user = v;
	},
	get accessToken() {
		return accessToken;
	},
	get refreshToken() {
		return refreshToken;
	},
	get memberships() {
		return memberships;
	},
	set memberships(v: TenantAccessResponse[]) {
		memberships = v;
	},
	get isAuthenticated() {
		return isAuthenticated;
	},
	setTokens,
	clearAuth
};
