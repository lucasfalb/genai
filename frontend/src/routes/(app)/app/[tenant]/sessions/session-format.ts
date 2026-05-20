import type { SessionListItem } from '$lib/api/types';

export function fmtCompactDatetime(iso: string) {
	return new Date(iso).toLocaleString('en-US', {
		month: 'short',
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit'
	});
}

export function fmtTime(iso: string) {
	return new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

export function shortId(id: string | null | undefined) {
	return id ? id.slice(0, 8) : '-';
}

export function envValue(session: SessionListItem | null, path: string) {
	let current: unknown = session?.environment;
	for (const part of path.split('.')) {
		if (!current || typeof current !== 'object') return null;
		current = (current as Record<string, unknown>)[part];
	}
	return typeof current === 'string' || typeof current === 'number' ? String(current) : null;
}

export function buildMetadataOptions(sessions: SessionListItem[], path: string) {
	return [
		...new Set(sessions.map((session) => envValue(session, path)).filter(Boolean) as string[])
	].sort((a, b) => a.localeCompare(b));
}

export function sessionTitle(
	session: SessionListItem | null,
	instanceNames: Map<string, string>,
	selectedSessionId?: string | null
) {
	if (!session) return selectedSessionId ? `Session ${shortId(selectedSessionId)}` : 'No session selected';
	if (session.user_ref && !isTechnicalRef(session.user_ref)) return session.user_ref;
	if (session.channel === 'widget') return `Visitor ${shortId(session.user_ref ?? session.id)}`;
	if (session.channel === 'api') return `API session ${shortId(session.id)}`;
	return `Session ${shortId(session.id)}`;
}

export function sessionAgent(session: SessionListItem | null, instanceNames: Map<string, string>) {
	if (!session) return 'Unknown agent';
	return instanceNames.get(session.instance_id) ?? shortId(session.instance_id);
}

export function sessionInitial(session: SessionListItem, instanceNames: Map<string, string>) {
	return sessionTitle(session, instanceNames).slice(0, 1).toUpperCase();
}

export function isLiveSession(session: SessionListItem | null) {
	return Boolean(session?.is_live);
}

export function messageInitial(role: string) {
	return role === 'user' ? 'U' : role === 'assistant' ? 'A' : role.slice(0, 1).toUpperCase();
}

export function browserLabel(session: SessionListItem | null) {
	const name = envValue(session, 'browser.name');
	const version = envValue(session, 'browser.version');
	return name ? `${name}${version ? ` ${version.split('.')[0]}` : ''}` : '-';
}

export function deviceLabel(session: SessionListItem | null) {
	const type = envValue(session, 'device.type');
	const os = envValue(session, 'os.name');
	return [type, os].filter(Boolean).join(' · ') || '-';
}

export function locationLabel(session: SessionListItem | null) {
	const city = envValue(session, 'geo.city');
	const region = envValue(session, 'geo.region');
	const country = envValue(session, 'geo.country_name') ?? envValue(session, 'geo.country');
	return [city, region, country].filter(Boolean).join(', ') || '-';
}

export function sessionMetaItems(session: SessionListItem | null, instanceNames: Map<string, string>) {
	if (!session) return [];
	return [
		sessionAgent(session, instanceNames),
		session.channel,
		`${session.message_count} messages`,
		`Started ${fmtCompactDatetime(session.started_at)}`,
		session.last_message_at ? `Last activity ${fmtCompactDatetime(session.last_message_at)}` : null
	].filter(Boolean) as string[];
}

export function environmentMetaItems(session: SessionListItem | null) {
	if (!session) return [];
	return [
		deviceLabel(session),
		browserLabel(session),
		locationLabel(session),
		envValue(session, 'device.timezone') ?? envValue(session, 'geo.timezone') ?? '-'
	].filter((item) => item && item !== '-') as string[];
}

function isTechnicalRef(value: string) {
	return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
}
