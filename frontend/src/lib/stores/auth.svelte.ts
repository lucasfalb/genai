import { browser } from '$app/environment';
import type { AuthMeResponse, TenantAccessResponse } from '$lib/api/types';

const LS_ACCESS = 'genai_access_token';
const LS_REFRESH = 'genai_refresh_token';
const COOKIE_MAX_AGE = 60 * 60 * 24 * 30;

let user = $state<AuthMeResponse | null>(null);
let accessToken = $state<string | null>(null);
let refreshToken = $state<string | null>(null);
let memberships = $state<TenantAccessResponse[]>([]);

const isAuthenticated = $derived(accessToken !== null);

function loadFromLocalStorage() {
	if (!browser) return;
	accessToken = localStorage.getItem(LS_ACCESS);
	refreshToken = localStorage.getItem(LS_REFRESH);
}

function setTokens(access: string, refresh: string) {
	accessToken = access;
	refreshToken = refresh;
	if (browser) {
		localStorage.setItem(LS_ACCESS, access);
		localStorage.setItem(LS_REFRESH, refresh);
		document.cookie = `${LS_ACCESS}=${encodeURIComponent(access)}; path=/; max-age=${COOKIE_MAX_AGE}; samesite=lax`;
		document.cookie = `${LS_REFRESH}=${encodeURIComponent(refresh)}; path=/; max-age=${COOKIE_MAX_AGE}; samesite=lax`;
	}
}

function clearAuth() {
	user = null;
	accessToken = null;
	refreshToken = null;
	memberships = [];
	if (browser) {
		localStorage.removeItem(LS_ACCESS);
		localStorage.removeItem(LS_REFRESH);
		document.cookie = `${LS_ACCESS}=; path=/; max-age=0; samesite=lax`;
		document.cookie = `${LS_REFRESH}=; path=/; max-age=0; samesite=lax`;
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
	loadFromLocalStorage,
	setTokens,
	clearAuth
};
