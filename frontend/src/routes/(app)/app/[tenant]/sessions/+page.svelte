<script lang="ts">
	import { replaceState } from '$app/navigation';
	import { page } from '$app/state';
	import { tick, untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { ApiError, api, getErrorMessage } from '$lib/api/client';
	import type { AgentInstanceResponse, SessionListItem, SessionMessageItem } from '$lib/api/types';
	import type { PageData } from './$types';
	import AdvancedFiltersDialog from './advanced-filters-dialog.svelte';
	import SessionHeader from './session-header.svelte';
	import SessionSidebar from './session-sidebar.svelte';
	import SessionTranscript from './session-transcript.svelte';
	import { buildMetadataOptions, envValue } from './session-format';

	let { data }: { data: PageData } = $props();

	const PAGE_SIZE = 50;

	let sessions = $state<SessionListItem[]>(data.sessions);
	let instances = $state<AgentInstanceResponse[]>(data.instances);
	let loading = $state(false);
	let loadingMore = $state(false);
	let hasMore = $state(data.hasMore);
	let selectedSessionId = $state<string | null>(page.url.searchParams.get('session'));
	let selectedSession = $state<SessionListItem | null>(null);
	let selectedMessages = $state<SessionMessageItem[]>([]);
	let selectedMessagesSessionId = $state<string | null>(null);
	let loadingMessages = $state(page.url.searchParams.has('session'));
	let sessionNotFound = $state(false);
	let sentinel = $state<HTMLDivElement | null>(null);
	let conversationEl = $state<HTMLDivElement | null>(null);

	let searchTerm = $state('');
	let agentFilter = $state('all');
	let channelFilter = $state('all');
	let osFilter = $state('all');
	let browserFilter = $state('all');
	let cityFilter = $state('all');
	let filtersOpen = $state(false);
	let filterReloadTimer: ReturnType<typeof setTimeout> | undefined;
	let lastResolvedQueryKey = queryKey(buildQuery(PAGE_SIZE));
	let inFlightQueryKey: string | null = null;
	let requestSequence = 0;
	let loadMoreQueryKey: string | null = null;

	const instanceNames = $derived(new Map(instances.map((i) => [i.id, i.name])));

	const agentOptions = $derived([
		{ value: 'all', label: 'All Agents' },
		...instances.map((i) => ({ value: i.id, label: i.name }))
	]);

	const channels = $derived([...new Set(sessions.map((s) => s.channel))].sort());

	const channelOptions = $derived([
		{ value: 'all', label: 'All Channels' },
		...channels.map((c) => ({ value: c, label: c }))
	]);

	const osOptions = $derived(buildMetadataOptions(sessions, 'os.name'));
	const browserOptions = $derived(buildMetadataOptions(sessions, 'browser.name'));
	const cityOptions = $derived(buildMetadataOptions(sessions, 'geo.city'));

	const filteredSessions = $derived(
		sessions.filter((session) => {
			const term = searchTerm.trim().toLowerCase();
			if (term) {
				const haystack = [
					session.id,
					session.user_ref,
					session.channel,
					instanceNames.get(session.instance_id),
					session.instance_id,
					envValue(session, 'browser.name'),
					envValue(session, 'os.name'),
					envValue(session, 'geo.city'),
					envValue(session, 'geo.country_name')
				]
					.filter(Boolean)
					.join(' ')
					.toLowerCase();
				if (!haystack.includes(term)) return false;
			}
			if (osFilter !== 'all' && envValue(session, 'os.name') !== osFilter) return false;
			if (browserFilter !== 'all' && envValue(session, 'browser.name') !== browserFilter)
				return false;
			if (cityFilter !== 'all' && envValue(session, 'geo.city') !== cityFilter) return false;
			return true;
		})
	);

	const hasActiveFilters = $derived(
		searchTerm.trim() !== '' ||
			agentFilter !== 'all' ||
			channelFilter !== 'all' ||
			osFilter !== 'all' ||
			browserFilter !== 'all' ||
			cityFilter !== 'all'
	);

	const activeFilterCount = $derived(
		[searchTerm.trim(), agentFilter, channelFilter, osFilter, browserFilter, cityFilter].filter(
			(value, index) => (index === 0 ? value !== '' : value !== 'all')
		).length
	);

	const filterKey = $derived([agentFilter, channelFilter].join('|'));
	const selectedMessagesLoaded = $derived(
		!!selectedSessionId && selectedMessagesSessionId === selectedSessionId
	);

	$effect(() => {
		filterKey;
		if (filterReloadTimer) clearTimeout(filterReloadTimer);
		filterReloadTimer = setTimeout(() => {
			void loadSessions();
		}, 350);
		return () => {
			if (filterReloadTimer) clearTimeout(filterReloadTimer);
		};
	});

	$effect(() => {
		if (sentinel && hasMore && !loading && !loadingMore) {
			const observer = new IntersectionObserver(
				(entries) => {
					if (entries[0]?.isIntersecting && hasMore && !loadingMore) {
						void loadMore();
					}
				},
				{ rootMargin: '400px' }
			);
			observer.observe(sentinel);
			return () => observer.disconnect();
		}
	});

	$effect(() => {
		const sessionId = page.url.searchParams.get('session');
		if (sessionId) {
			untrack(() => {
				if (selectedSessionId !== sessionId || selectedMessagesSessionId !== sessionId) {
					void selectSessionById(sessionId, { updateUrl: false });
				}
			});
			return;
		}
		untrack(() => {
			if (!selectedSessionId && sessions.length > 0) {
				void selectSession(sessions[0]);
			}
		});
	});

	$effect(() => {
		if (!selectedSessionId) return;
		const found = sessions.find((s) => s.id === selectedSessionId);
		if (found) {
			selectedSession = found;
		}
	});

	$effect(() => {
		selectedMessages.length;
		loadingMessages;
		void scrollConversationToBottom();
	});

	async function loadSessions(options: { force?: boolean } = {}) {
		const q = buildQuery(PAGE_SIZE);
		const k = queryKey(q);
		if (!options.force && k === lastResolvedQueryKey) return;
		if (k === inFlightQueryKey) return;

		const requestId = ++requestSequence;
		inFlightQueryKey = k;
		loading = true;
		try {
			const params = new URLSearchParams();
			for (const [key, value] of Object.entries(q)) {
				if (value !== undefined && value !== null && String(value) !== '') {
					params.set(key, String(value));
				}
			}
			const res = await api.get<SessionListItem[]>(`/tenant/sessions?${params}`);
			if (requestId !== requestSequence) return;
			sessions = res;
			hasMore = res.length >= PAGE_SIZE;
			lastResolvedQueryKey = k;
			if (!page.url.searchParams.get('session') && res.length > 0) {
				void selectSession(res[0]);
			}
		} catch (err) {
			if (requestId !== requestSequence) return;
			toast.error(getErrorMessage(err, 'Could not load sessions.'));
		} finally {
			if (requestId === requestSequence) {
				loading = false;
				inFlightQueryKey = null;
			}
		}
	}

	async function loadMore() {
		if (loadingMore || !hasMore) return;
		const newLimit = sessions.length + PAGE_SIZE;
		const q = buildQuery(newLimit);
		const k = queryKey(q);
		if (k === loadMoreQueryKey) return;

		loadingMore = true;
		loadMoreQueryKey = k;
		try {
			const params = new URLSearchParams();
			for (const [key, value] of Object.entries(q)) {
				if (value !== undefined && value !== null && String(value) !== '') {
					params.set(key, String(value));
				}
			}
			const data = await api.get<SessionListItem[]>(`/tenant/sessions?${params}`);
			const existingIds = new Set(sessions.map((s) => s.id));
			for (const s of data) {
				if (!existingIds.has(s.id)) sessions = [...sessions, s];
			}
			if (data.length < newLimit) hasMore = false;
		} catch {
			hasMore = false;
		} finally {
			loadingMore = false;
			loadMoreQueryKey = null;
		}
	}

	async function selectSession(session: SessionListItem, options: { updateUrl?: boolean } = {}) {
		selectedSession = session;
		await selectSessionById(session.id, options);
	}

	async function selectSessionById(id: string, options: { updateUrl?: boolean } = {}) {
		selectedSessionId = id;
		sessionNotFound = false;
		if (selectedMessagesSessionId !== id) {
			loadingMessages = true;
			selectedMessages = [];
		}
		if (options.updateUrl !== false) setSessionParam(id);

		const session = await resolveSession(id);
		if (!session) {
			loadingMessages = false;
			return;
		}
		selectedSession = session;

		if (selectedMessagesSessionId !== id) {
			try {
				selectedMessages = await api.get<SessionMessageItem[]>(`/tenant/sessions/${id}/messages`);
				selectedMessagesSessionId = id;
				sessionNotFound = false;
				await scrollConversationToBottom();
			} catch (err) {
				selectedMessagesSessionId = id;
				if (
					err instanceof ApiError &&
					(err.status === 404 || (err.status === 422 && err.code === 'VALIDATION_ERROR'))
				) {
					sessionNotFound = true;
				} else {
					toast.error(getErrorMessage(err, 'Could not load messages.'));
				}
			} finally {
				loadingMessages = false;
			}
		} else {
			loadingMessages = false;
		}
	}

	async function resolveSession(id: string) {
		const found = sessions.find((s) => s.id === id);
		if (found) return found;
		try {
			const session = await api.get<SessionListItem>(`/tenant/sessions/${id}`);
			if (!sessions.some((s) => s.id === session.id)) {
				sessions = [session, ...sessions];
			}
			return session;
		} catch (err) {
			selectedMessages = [];
			selectedMessagesSessionId = id;
			if (
				err instanceof ApiError &&
				(err.status === 404 || (err.status === 422 && err.code === 'VALIDATION_ERROR'))
			) {
				sessionNotFound = true;
			} else {
				toast.error(getErrorMessage(err, 'Could not load session.'));
			}
			return null;
		}
	}

	function setSessionParam(id: string | null) {
		const next = new URL(page.url);
		if (id) {
			next.searchParams.set('session', id);
		} else {
			next.searchParams.delete('session');
		}
		if (`${next.pathname}${next.search}` === `${page.url.pathname}${page.url.search}`) return;
		replaceState(`${next.pathname}${next.search}`, page.state);
	}

	function clearFilters() {
		searchTerm = '';
		agentFilter = 'all';
		channelFilter = 'all';
		osFilter = 'all';
		browserFilter = 'all';
		cityFilter = 'all';
	}

	function openMostRecentSession() {
		const nextSession = sessions[0];
		if (nextSession) {
			void selectSession(nextSession);
		} else {
			selectedSessionId = null;
			selectedSession = null;
			selectedMessages = [];
			selectedMessagesSessionId = null;
			sessionNotFound = false;
			setSessionParam(null);
		}
	}

	async function scrollConversationToBottom() {
		await tick();
		if (conversationEl) {
			conversationEl.scrollTop = conversationEl.scrollHeight;
		}
	}

	function buildQuery(limit: number) {
		const params: Record<string, string | number | undefined> = { limit };
		if (agentFilter !== 'all') params.instance_id = agentFilter;
		if (channelFilter !== 'all') params.channel = channelFilter;
		return params;
	}

	function queryKey(params: Record<string, string | number | undefined>) {
		const q = new URLSearchParams();
		for (const [k, v] of Object.entries(params)) {
			if (v !== undefined && v !== null && String(v) !== '') q.set(k, String(v));
		}
		q.sort();
		return q.toString();
	}
</script>

<div class="flex h-full flex-col">
	<div class="flex min-h-0 flex-1 flex-col overflow-hidden bg-card lg:flex-row">
		<SessionSidebar
			sessions={filteredSessions}
			{selectedSessionId}
			{instanceNames}
			{loading}
			{loadingMore}
			{hasActiveFilters}
			{activeFilterCount}
			bind:searchTerm
			bind:sentinel
			openFilters={() => {
				filtersOpen = true;
			}}
			{clearFilters}
			refresh={() => loadSessions({ force: true })}
			selectSession={(session) => void selectSession(session)}
		/>

		<main class="flex min-h-0 min-w-0 flex-1 flex-col bg-background">
			<SessionHeader session={selectedSession} {selectedSessionId} {instanceNames} />
			<SessionTranscript
				{selectedSessionId}
				messages={selectedMessages}
				{loadingMessages}
				messagesLoaded={selectedMessagesLoaded}
				{sessionNotFound}
				bind:conversationEl
				{openMostRecentSession}
			/>
		</main>
	</div>

	<AdvancedFiltersDialog
		bind:open={filtersOpen}
		bind:searchTerm
		bind:agentFilter
		bind:channelFilter
		bind:osFilter
		bind:browserFilter
		bind:cityFilter
		{agentOptions}
		{channelOptions}
		{osOptions}
		{browserOptions}
		{cityOptions}
		{hasActiveFilters}
		{clearFilters}
	/>
</div>
