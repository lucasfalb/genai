<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import * as LucideIcons from '@lucide/svelte/icons';
	import Bot from '@lucide/svelte/icons/bot';
	import Settings2 from '@lucide/svelte/icons/settings-2';
	import Mic from '@lucide/svelte/icons/mic';
	import MicOff from '@lucide/svelte/icons/mic-off';
	import MessageCircle from '@lucide/svelte/icons/message-circle';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Send from '@lucide/svelte/icons/send';
	import Square from '@lucide/svelte/icons/square';
	import X from '@lucide/svelte/icons/x';
	import type { WebWidgetConfig } from '$lib/api/types';
	import { widgetDefaultMessages, widgetLocaleMessages } from '$lib/data/widget-locales';
	import type { UiMessageKey } from '$lib/data/widget-locales';
	import { renderFormattedMessage } from '$lib/utils/rich-message';

	let {
		instanceId,
		apiBase
	}: {
		instanceId: string;
		apiBase: string;
	} = $props();

	type Message = {
		role: 'user' | 'assistant';
		content: string;
		pending?: boolean;
		error?: boolean;
	};
	type WidgetSessionResponse = { session_id: string | null; messages: Message[] };
	type SpeechRecognitionEventLike = Event & {
		results: SpeechRecognitionResultList;
		resultIndex: number;
	};
	type SpeechRecognitionErrorEventLike = Event & { error?: string };
	type SpeechRecognitionLike = EventTarget & {
		continuous: boolean;
		interimResults: boolean;
		lang: string;
		start: () => void;
		stop: () => void;
		abort: () => void;
		onresult: ((event: SpeechRecognitionEventLike) => void) | null;
		onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
		onend: (() => void) | null;
	};

	const iconRegistry = LucideIcons as unknown as Record<string, typeof MessageCircle>;
	const dismissedKey = $derived(`genai-widget-dismissed-${instanceId}`);
	const visitorStorageKey = $derived(`genai_widget_visitor_${instanceId}`);

	let cfg = $state<WebWidgetConfig | null>(null);
	let configError = $state('');
	let open = $state(false);
	let userDismissed = $state(false);
	let inputValue = $state('');
	let messages = $state<Message[]>([]);
	let sessionId = $state<string | null>(null);
	let streaming = $state(false);
	let lastFailedText = $state<string | null>(null);
	let messagesEl = $state<HTMLDivElement | null>(null);
	let textareaEl = $state<HTMLTextAreaElement | null>(null);
	let panelEl = $state<HTMLElement | null>(null);
	let launcherEl = $state<HTMLButtonElement | null>(null);
	let abortController: AbortController | null = null;
	let userInteracted = false;
	let accessibilityOpen = $state(false);
	let textScale = $state(0);
	let highContrast = $state(false);
	let reduceMotion = $state(false);
	let screenReaderMode = $state(false);
	let voiceSupported = $state(false);
	let listening = $state(false);
	let voiceStatus = $state('');
	let liveAnnouncement = $state('');
	let speechRecognition: SpeechRecognitionLike | null = null;
	let voiceStatusTimer: ReturnType<typeof setTimeout> | null = null;
	let presenceTimer: ReturnType<typeof setInterval> | null = null;

	function setVoiceStatus(text: string, transient = false) {
		if (voiceStatusTimer) { clearTimeout(voiceStatusTimer); voiceStatusTimer = null; }
		voiceStatus = text;
		if (transient && text) {
			voiceStatusTimer = setTimeout(() => { voiceStatus = ''; voiceStatusTimer = null; }, 4000);
		}
	}

	const radiusMap = { sharp: '0px', rounded: '18px', full: '26px' };
	const radius = $derived(cfg ? (radiusMap[cfg.border_radius] ?? '18px') : '18px');
	const LauncherIcon = $derived(getLucideIcon(cfg?.launcher_icon || 'message-circle'));
	const AvatarIcon = $derived(getLucideIcon(cfg?.avatar_icon || 'bot') ?? Bot);
	const unreadBadgeVisible = $derived(
		!!cfg?.show_unread_badge && !open && messages.filter((m) => m.role === 'user').length === 0
	);
	const quickRepliesVisible = $derived(
		!!cfg &&
			cfg.quick_replies.length > 0 &&
			!streaming &&
			messages.filter((m) => m.role === 'user').length === 0
	);
	const canUseVoice = $derived(voiceSupported && !streaming);
	const textScaleLabel = $derived(textScale === 0 ? 'Default' : textScale === 1 ? 'Large' : 'Largest');

	function resolveSupportedLocale(locale: string | null | undefined): string | null {
		if (!locale) return null;
		const normalized = locale.replace('_', '-');
		const supported = Object.keys(widgetLocaleMessages);
		const exact = supported.find((item) => item.toLowerCase() === normalized.toLowerCase());
		if (exact) return exact;
		const base = normalized.split('-')[0].toLowerCase();
		return supported.find((item) => item.toLowerCase().startsWith(base + '-')) ?? null;
	}

	function getConfiguredLocaleMessage(locale: string | null | undefined, key: UiMessageKey): string | null {
		if (!cfg?.ui_messages || !locale) return null;
		const supportedLocale = resolveSupportedLocale(locale) ?? locale;
		const exact = cfg.ui_messages[supportedLocale];
		if (exact && typeof exact === 'object') return exact[key] || null;
		const base = supportedLocale.split('-')[0].toLowerCase();
		const baseMatch = Object.entries(cfg.ui_messages).find(
			([entryLocale, messages]) =>
				typeof messages === 'object' && entryLocale.toLowerCase().startsWith(base + '-')
		)?.[1];
		if (baseMatch && typeof baseMatch === 'object') return baseMatch[key] || null;
		return null;
	}

	function getFlatFallbackMessage(key: UiMessageKey): string | null {
		const value = cfg?.ui_messages?.[key];
		return typeof value === 'string' ? value : null;
	}

	function getBuiltInLocaleMessage(locale: string | null | undefined, key: UiMessageKey): string | null {
		const supportedLocale = resolveSupportedLocale(locale);
		if (!supportedLocale) return null;
		const byLocale = widgetLocaleMessages[supportedLocale] ?? widgetLocaleMessages[supportedLocale.split('-')[0]];
		return byLocale?.[key] ?? null;
	}

	const effectiveLocale = $derived.by(() => {
		const pageLocale =
			typeof document !== 'undefined' ? document.documentElement.getAttribute('lang') : null;
		const configuredLocale = cfg?.locale;

		for (const locale of [pageLocale, configuredLocale]) {
			const supportedLocale = resolveSupportedLocale(locale);
			if (supportedLocale) return supportedLocale;
		}

		return cfg?.locale || 'en-US';
	});

	function msg(key: UiMessageKey): string {
		const fallbackLocale = cfg?.locale || 'en-US';
		const effectiveConfigured = getConfiguredLocaleMessage(effectiveLocale, key);
		if (effectiveConfigured) return effectiveConfigured;
		const effectiveBuiltIn = getBuiltInLocaleMessage(effectiveLocale, key);
		if (effectiveBuiltIn && effectiveLocale !== resolveSupportedLocale(fallbackLocale)) return effectiveBuiltIn;
		const fallbackConfigured =
			getConfiguredLocaleMessage(fallbackLocale, key) ?? getFlatFallbackMessage(key);
		if (fallbackConfigured) return fallbackConfigured;
		return effectiveBuiltIn ?? getBuiltInLocaleMessage(fallbackLocale, key) ?? widgetDefaultMessages[key];
	}

	function kebabToPascal(value: string) {
		return value
			.split('-')
			.map((part) => part.charAt(0).toUpperCase() + part.slice(1))
			.join('');
	}

	function getLucideIcon(value: string | null | undefined) {
		return iconRegistry[kebabToPascal(value || '')] ?? MessageCircle;
	}

	function initials(name: string | undefined): string {
		return (
			(name || 'AI')
				.split(' ')
				.map((w) => w[0])
				.join('')
				.slice(0, 2)
				.toUpperCase() || 'AI'
		);
	}

	function getVisitorId() {
		const value = crypto.randomUUID();
		try {
			const existing = sessionStorage.getItem(visitorStorageKey);
			if (existing) return existing;
			sessionStorage.setItem(visitorStorageKey, value);
		} catch {
			// Session storage can be blocked; fall back to an in-memory id for this page.
		}
		return value;
	}

	function seedOpeningMessage(config: WebWidgetConfig) {
		if (messages.length > 0) return;
		messages = [
			{
				role: 'assistant',
				content: config.opening_message || msg('default_opening_message')
			}
		];
	}

	function normalizeConfig(data: Partial<WebWidgetConfig>): WebWidgetConfig {
		return {
			title: data.title || 'Chat with us',
			subtitle: data.subtitle || '',
			bot_name: data.bot_name || 'Assistant',
			primary_color: data.primary_color || '#3b82f6',
			bg_color: data.bg_color || '#ffffff',
			border_radius: data.border_radius || 'rounded',
			position: data.position || 'bottom-right',
			font_family: data.font_family || 'system',
			locale: data.locale || 'en-US',
			avatar_mode: data.avatar_mode || 'initials',
			avatar_icon: data.avatar_icon || 'bot',
			avatar_image_url: data.avatar_image_url || null,
			launcher_mode: data.launcher_mode || 'icon',
			launcher_icon: data.launcher_icon || 'message-circle',
			launcher_image_url: data.launcher_image_url || null,
			auto_open_delay: data.auto_open_delay ?? null,
			show_unread_badge: data.show_unread_badge ?? true,
			opening_message: data.opening_message || null,
			quick_replies: Array.isArray(data.quick_replies) ? data.quick_replies : [],
			sound_enabled: data.sound_enabled ?? false,
			typing_indicator: data.typing_indicator ?? true,
			mobile_fullscreen: data.mobile_fullscreen ?? true,
			ui_messages: data.ui_messages || {}
		};
	}

	async function loadConfig() {
		const response = await fetch(`${apiBase}/public/widget/${instanceId}/config`);
		if (!response.ok) throw new Error(`${response.status}`);
		const body = await response.json();
		if (body.status !== 'success') throw new Error('Invalid response');
		return normalizeConfig(body.data || {});
	}

	async function loadServerSession(config: WebWidgetConfig) {
		const response = await fetch(`${apiBase}/public/widget/${instanceId}/session`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ visitor_id: getVisitorId() })
		});
		if (!response.ok) {
			seedOpeningMessage(config);
			return;
		}
		const body = await response.json();
		const data = body.data as WidgetSessionResponse;
		sessionId = data.session_id;
		messages = Array.isArray(data.messages) ? data.messages : [];
		seedOpeningMessage(config);
	}

	async function touchServerSession() {
		if (!sessionId) return;
		try {
			await fetch(`${apiBase}/public/widget/${instanceId}/session`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ visitor_id: getVisitorId() })
			});
		} catch {
			// Presence is best-effort and should never interrupt the widget.
		}
	}

	function applyFont(config: WebWidgetConfig) {
		if (config.font_family === 'inherit') {
			document.documentElement.style.setProperty('--genai-widget-font', 'inherit');
			return;
		}
		if (config.font_family === 'system') {
			document.documentElement.style.setProperty(
				'--genai-widget-font',
				"-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
			);
			return;
		}
		const id = `genai-widget-font-${config.font_family.replace(/\s+/g, '-').toLowerCase()}`;
		if (!document.getElementById(id)) {
			const link = document.createElement('link');
			link.id = id;
			link.rel = 'stylesheet';
			link.href = `https://fonts.googleapis.com/css2?family=${encodeURIComponent(config.font_family)}:wght@400;500;600;700&display=swap`;
			document.head.appendChild(link);
		}
		document.documentElement.style.setProperty(
			'--genai-widget-font',
			`'${config.font_family}', sans-serif`
		);
	}

	function openWidget() {
		userInteracted = true;
		open = true;
		liveAnnouncement = msg('chat_opened');
		requestAnimationFrame(() => textareaEl?.focus());
	}

	function toggleA11yPanel() {
		accessibilityOpen = !accessibilityOpen;
		announce(accessibilityOpen ? msg('accessibility_opened') : msg('accessibility_closed'));
	}

	function closeWidget() {
		userInteracted = true;
		userDismissed = true;
		open = false;
		accessibilityOpen = false;
		stopListening();
		liveAnnouncement = msg('chat_closed');
		try {
			sessionStorage.setItem(dismissedKey, '1');
		} catch {
			// Optional dismissal memory only.
		}
		requestAnimationFrame(() => launcherEl?.focus());
	}

	function scrollToBottom() {
		requestAnimationFrame(() => {
			if (messagesEl) messagesEl.scrollTop = messagesEl.scrollHeight;
		});
	}

	function autosizeInput() {
		if (!textareaEl) return;
		textareaEl.style.height = 'auto';
		textareaEl.style.height = `${Math.min(textareaEl.scrollHeight, 96)}px`;
	}

	function announce(message: string) {
		liveAnnouncement = '';
		requestAnimationFrame(() => {
			liveAnnouncement = message;
		});
	}

	function playNotification() {
		if (!cfg?.sound_enabled || !userInteracted) return;
		try {
			const AudioContextCtor =
				window.AudioContext ||
				(window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
			if (!AudioContextCtor) return;
			const ctx = new AudioContextCtor();
			const osc = ctx.createOscillator();
			const gain = ctx.createGain();
			osc.frequency.value = 740;
			gain.gain.setValueAtTime(0.0001, ctx.currentTime);
			gain.gain.exponentialRampToValueAtTime(0.05, ctx.currentTime + 0.02);
			gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.16);
			osc.connect(gain);
			gain.connect(ctx.destination);
			osc.start();
			osc.stop(ctx.currentTime + 0.18);
			setTimeout(() => ctx.close(), 250);
		} catch {
			// Browsers can block audio until interaction.
		}
	}

	function collectEnvironment() {
		const ua = navigator.userAgent || '';
		return {
			page: {
				url: window.location.href,
				referrer: document.referrer || null
			},
			device: {
				type: getDeviceType(),
				language: navigator.language || null,
				languages: Array.from(navigator.languages || []),
				timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || null,
				viewport: { width: window.innerWidth, height: window.innerHeight },
				screen: {
					width: window.screen?.width ?? null,
					height: window.screen?.height ?? null,
					pixel_ratio: window.devicePixelRatio || 1
				}
			},
			browser: {
				...parseBrowser(ua),
				user_agent: ua
			},
			os: parseOs(ua)
		};
	}

	function getDeviceType() {
		const ua = navigator.userAgent || '';
		if (/ipad|tablet/i.test(ua)) return 'tablet';
		if (/mobi|android|iphone|ipod/i.test(ua)) return 'mobile';
		return 'desktop';
	}

	function parseBrowser(ua: string) {
		const rules: Array<[string, RegExp]> = [
			['Edge', /Edg\/([\d.]+)/],
			['Chrome', /Chrome\/([\d.]+)/],
			['Firefox', /Firefox\/([\d.]+)/],
			['Safari', /Version\/([\d.]+).*Safari/]
		];
		for (const [name, pattern] of rules) {
			const match = ua.match(pattern);
			if (match) return { name, version: match[1] ?? null };
		}
		return { name: 'Unknown', version: null };
	}

	function parseOs(ua: string) {
		const rules: Array<[string, RegExp]> = [
			['iOS', /(?:iPhone|iPad|iPod).*OS ([\d_]+)/],
			['Android', /Android ([\d.]+)/],
			['macOS', /Mac OS X ([\d_]+)/],
			['Windows', /Windows NT ([\d.]+)/],
			['Linux', /Linux/]
		];
		for (const [name, pattern] of rules) {
			const match = ua.match(pattern);
			if (match) return { name, version: match[1]?.replace(/_/g, '.') ?? null };
		}
		return { name: 'Unknown', version: null };
	}

	async function sendMessage(textOverride?: string) {
		if (!cfg) return;
		const text = (textOverride ?? inputValue).trim();
		if (!text || streaming) return;
		userInteracted = true;
		stopListening();
		inputValue = '';
		lastFailedText = null;
		announce(msg('message_sent'));
		messages = [
			...messages.filter((m) => !m.error),
			{ role: 'user', content: text },
			{ role: 'assistant', content: '', pending: true }
		];
		const assistantIdx = messages.length - 1;
		streaming = true;
		abortController = new AbortController();

		try {
			const res = await fetch(`${apiBase}/public/widget/${instanceId}/chat`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
				body: JSON.stringify({
					message: text,
					session_id: sessionId,
					metadata: { visitor_id: getVisitorId(), environment: collectEnvironment() }
				}),
				signal: abortController.signal
			});
			if (!res.ok || !res.body) throw new Error(`${res.status}`);
			const reader = res.body.getReader();
			const decoder = new TextDecoder();
			let buffer = '';
			let accumulated = '';

			while (true) {
				const { value, done } = await reader.read();
				if (done) break;
				buffer += decoder.decode(value, { stream: true });
				let sep = buffer.indexOf('\n\n');
				while (sep !== -1) {
					const block = buffer.slice(0, sep);
					buffer = buffer.slice(sep + 2);
					sep = buffer.indexOf('\n\n');
					for (const rawLine of block.split('\n')) {
						const line = rawLine.replace(/\r$/, '');
						if (!line || line.startsWith(':') || !line.startsWith('data:')) continue;
						const event = JSON.parse(line.slice(5).trimStart()) as {
							event: string;
							content?: string;
							session_id?: string;
						};
						if (event.session_id) sessionId = event.session_id;
						if (event.event === 'assistant.delta' && typeof event.content === 'string') {
							accumulated = event.content.startsWith(accumulated)
								? event.content
								: accumulated + event.content;
							messages[assistantIdx] = { role: 'assistant', content: accumulated };
							messages = messages;
						} else if (event.event === 'run.completed') {
							messages[assistantIdx] = { role: 'assistant', content: accumulated || 'Done.' };
							messages = messages;
						}
					}
				}
			}

			if (!accumulated.trim()) {
				messages[assistantIdx] = {
					role: 'assistant',
					content: msg('no_response'),
					error: true
				};
				lastFailedText = text;
				announce(msg('no_response'));
			} else {
				announce(msg('response_received'));
				playNotification();
			}
		} catch (err) {
			if ((err as { name?: string }).name === 'AbortError') {
				messages[assistantIdx] = { role: 'assistant', content: msg('response_stopped') };
				announce(msg('response_stopped'));
			} else {
				messages[assistantIdx] = {
					role: 'assistant',
					content: msg('message_failed'),
					error: true
				};
				lastFailedText = text;
				announce(msg('message_failed'));
			}
		} finally {
			streaming = false;
			abortController = null;
			messages = messages;
		}
	}

	function retryLastMessage() {
		if (!lastFailedText) return;
		const retryText = lastFailedText;
		messages = messages.filter((m) => !m.error);
		sendMessage(retryText);
	}

	function getSpeechRecognitionCtor() {
		return (
			(window as unknown as { SpeechRecognition?: new () => SpeechRecognitionLike }).SpeechRecognition ||
			(window as unknown as { webkitSpeechRecognition?: new () => SpeechRecognitionLike })
				.webkitSpeechRecognition
		);
	}

	function startListening() {
		if (!canUseVoice || listening) return;
		const Recognition = getSpeechRecognitionCtor();
		if (!Recognition) {
			voiceSupported = false;
			setVoiceStatus(msg('voice_unsupported'), true);
			announce(voiceStatus);
			return;
		}

		const recognition = new Recognition();
		speechRecognition = recognition;
		recognition.continuous = false;
		recognition.interimResults = true;
		recognition.lang = effectiveLocale;

		let finalTranscript = '';
		recognition.onresult = (event) => {
			let interimTranscript = '';
			for (let i = event.resultIndex; i < event.results.length; i += 1) {
				const transcript = event.results[i][0]?.transcript ?? '';
				if (event.results[i].isFinal) finalTranscript += transcript;
				else interimTranscript += transcript;
			}
			const transcript = `${finalTranscript} ${interimTranscript}`.trim();
			if (transcript) {
				inputValue = transcript;
				voiceStatus = interimTranscript ? msg('listening') : msg('voice_captured');
			}
		};
		recognition.onerror = (event) => {
			listening = false;
			setVoiceStatus(
				event.error === 'not-allowed'
					? msg('voice_permission_blocked')
					: msg('voice_try_again'),
				true
			);
			announce(voiceStatus);
		};
		recognition.onend = () => {
			listening = false;
			speechRecognition = null;
			if (inputValue.trim()) {
				setVoiceStatus(msg('voice_ready'), true);
				announce(voiceStatus);
			}
		};

		try {
			userInteracted = true;
			listening = true;
			setVoiceStatus(msg('listening'));
			announce(msg('listening_started'));
			recognition.start();
		} catch {
			listening = false;
			setVoiceStatus(msg('voice_start_failed'), true);
			announce(voiceStatus);
		}
	}

	function stopListening() {
		if (!speechRecognition) return;
		try {
			speechRecognition.stop();
		} catch {
			speechRecognition.abort();
		}
		listening = false;
	}

	function toggleListening() {
		if (listening) {
			stopListening();
			setVoiceStatus(inputValue.trim() ? msg('voice_ready') : msg('voice_stopped'), true);
			announce(voiceStatus);
		} else {
			startListening();
		}
	}

	function handlePanelKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			if (accessibilityOpen) {
				accessibilityOpen = false;
				announce(msg('accessibility_closed'));
			} else {
				closeWidget();
			}
			return;
		}

		if (e.key !== 'Tab' || !panelEl) return;
		const focusable = Array.from(
			panelEl.querySelectorAll<HTMLElement>(
				'button:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex="-1"])'
			)
		).filter((el) => !el.hasAttribute('hidden'));
		if (focusable.length === 0) return;
		const first = focusable[0];
		const last = focusable[focusable.length - 1];
		if (e.shiftKey && document.activeElement === first) {
			e.preventDefault();
			last.focus();
		} else if (!e.shiftKey && document.activeElement === last) {
			e.preventDefault();
			first.focus();
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			closeWidget();
			return;
		}
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			sendMessage();
		}
	}

	onMount(async () => {
		try {
			userDismissed = sessionStorage.getItem(dismissedKey) === '1';
		} catch {
			userDismissed = false;
		}
		voiceSupported = !!getSpeechRecognitionCtor();

		try {
			const config = await loadConfig();
			applyFont(config);
			cfg = config;
			await loadServerSession(config);
			presenceTimer = setInterval(touchServerSession, 30_000);
			if (!userDismissed && config.auto_open_delay != null && config.auto_open_delay > 0) {
				setTimeout(() => {
					if (!userDismissed && !open) open = true;
				}, config.auto_open_delay * 1000);
			}
		} catch {
			configError = 'The chat widget is currently unavailable.';
		}
	});

	onDestroy(() => {
		if (presenceTimer) clearInterval(presenceTimer);
	});

	$effect(() => {
		messages;
		scrollToBottom();
	});

	$effect(() => {
		inputValue;
		autosizeInput();
	});
</script>

<div
	class:high-contrast={highContrast}
	class:text-large={textScale === 1}
	class:text-largest={textScale === 2}
	class:reduce-motion={reduceMotion}
	class:screen-reader-mode={screenReaderMode}
	class:error={!!configError}
	class:left={cfg?.position === 'bottom-left'}
	class:mobile-fullscreen={cfg?.mobile_fullscreen}
	class:open
	class="widget-shell"
	style:--widget-primary={cfg?.primary_color}
	style:--widget-bg={cfg?.bg_color}
	style:--widget-radius={radius}
>
	<div class="sr-only" role="status" aria-live="polite" aria-atomic="true">{liveAnnouncement}</div>
	{#if configError}
		<div class="state-error" role="status">
			<strong>Chat unavailable</strong>
			<p>{configError}</p>
		</div>
	{:else if cfg && !open}
		<button
			bind:this={launcherEl}
			class="launcher"
			onclick={openWidget}
			aria-label="Open chat"
			aria-haspopup="dialog"
			aria-expanded={open}
		>
			{#if unreadBadgeVisible}<span class="launcher-pulse"></span>{/if}
			{#if cfg.launcher_mode === 'image' && cfg.launcher_image_url}
				<img class="launcher-image" src={cfg.launcher_image_url} alt="" />
			{:else}
				<LauncherIcon size={30} />
			{/if}
			{#if unreadBadgeVisible}<span class="badge" aria-hidden="true"></span>{/if}
		</button>
	{:else if cfg && open}
		<div
			bind:this={panelEl}
			class="panel"
			role="dialog"
			tabindex="-1"
			aria-modal="false"
			aria-labelledby="genai-widget-title"
			onkeydown={handlePanelKeydown}
		>
			<header class="header">
				<div class="header-row">
					<div class="avatar" aria-hidden="true">
						{#if cfg.avatar_mode === 'image' && cfg.avatar_image_url}
							<img src={cfg.avatar_image_url} alt="" />
						{:else if cfg.avatar_mode === 'icon'}
							<AvatarIcon size={22} />
						{:else}
							{initials(cfg.bot_name)}
						{/if}
					</div>
					<div class="title-wrap">
						<div id="genai-widget-title" class="title">{cfg.title}</div>
						{#if cfg.subtitle}
							<div class="subtitle">{cfg.subtitle}</div>
						{/if}
					</div>
					<button
						class="header-button"
						class:active={accessibilityOpen}
						onclick={toggleA11yPanel}
						aria-label={msg('accessibility_controls')}
						aria-controls="genai-widget-a11y"
						aria-expanded={accessibilityOpen}
					>
						<Settings2 size={16} />
					</button>
					<button class="close-button" onclick={closeWidget} aria-label="Close chat"
						><X size={18} /></button
					>
				</div>
				{#if accessibilityOpen}
					<div id="genai-widget-a11y" class="a11y-panel" role="group" aria-label={msg('accessibility_controls')}>
						<div class="a11y-row">
							<span class="a11y-label">Text size<em>{textScaleLabel}</em></span>
							<div class="a11y-stepper">
								<button onclick={() => (textScale = Math.max(0, textScale - 1))} disabled={textScale === 0} aria-label="Decrease text size">A−</button>
								<button onclick={() => (textScale = Math.min(2, textScale + 1))} disabled={textScale === 2} aria-label="Increase text size">A+</button>
							</div>
						</div>
						<label class="a11y-row a11y-toggle">
							<span class="a11y-label">High contrast</span>
							<input type="checkbox" bind:checked={highContrast} />
						</label>
						<label class="a11y-row a11y-toggle">
							<span class="a11y-label">Reduce motion</span>
							<input type="checkbox" bind:checked={reduceMotion} />
						</label>
						<label class="a11y-row a11y-toggle">
							<span class="a11y-label">Screen reader mode</span>
							<input type="checkbox" bind:checked={screenReaderMode} />
						</label>
					</div>
				{/if}
			</header>

			<div
				bind:this={messagesEl}
				class="messages"
				role="log"
				aria-live="polite"
				aria-relevant="additions text"
				aria-label="Chat messages"
			>
				{#each messages as message}
					{#if message.role === 'assistant'}
						<div class="message-row assistant">
							<div class="avatar small" aria-hidden="true">
								{#if cfg.avatar_mode === 'icon'}<AvatarIcon size={15} />{:else}{initials(
										cfg.bot_name
									)}{/if}
							</div>
							<div
								class:error={message.error}
								class="bubble assistant"
								role={message.error ? 'alert' : undefined}
								aria-label={`${cfg.bot_name}: ${message.content || 'typing'}`}
							>
								{#if message.pending && !message.content && cfg.typing_indicator}
									<span class="typing" aria-label={msg('typing_label')}
										><span></span><span></span><span></span></span
									>
								{:else}
									<div class="rich-message">{@html renderFormattedMessage(message.content)}</div>
									{#if message.error && lastFailedText}
										<button class="retry-button" onclick={retryLastMessage}
											><RefreshCw size={13} /> {msg('retry_message')}</button
										>
									{/if}
								{/if}
							</div>
						</div>
					{:else}
						<div class="message-row user">
							<div class="bubble user" aria-label={`You: ${message.content}`}>
								<div class="rich-message">{@html renderFormattedMessage(message.content)}</div>
							</div>
						</div>
					{/if}
				{/each}

				{#if quickRepliesVisible}
					<div class="quick-replies" aria-label="Suggested replies">
						{#each cfg.quick_replies as reply}
							<button class="quick-reply" onclick={() => sendMessage(reply)}>{reply}</button>
						{/each}
					</div>
				{/if}
			</div>

			<footer class="composer">
				{#if voiceStatus}
					<div id="genai-widget-voice-status" class="voice-status" role="status" aria-live="polite">
						{voiceStatus}
					</div>
				{/if}
				<div class="composer-inner">
					<textarea
						bind:this={textareaEl}
						bind:value={inputValue}
						onkeydown={handleKeydown}
						placeholder={streaming ? msg('waiting_placeholder') : msg('input_placeholder')}
						disabled={streaming}
						rows="1"
						aria-label="Message"
						aria-describedby={voiceStatus ? 'genai-widget-voice-status' : undefined}
					></textarea>
					<button
						class:listening
						class="mic-button"
						onclick={toggleListening}
						disabled={!canUseVoice}
						aria-label={listening ? msg('stop_microphone') : msg('use_microphone')}
						aria-pressed={listening}
						title={voiceSupported ? msg('use_microphone') : msg('voice_unsupported')}
					>
						{#if listening}<MicOff size={16} />{:else}<Mic size={16} />{/if}
					</button>
					{#if streaming}
						<button
							class="send-button"
							onclick={() => abortController?.abort()}
							aria-label={msg('response_stopped')}><Square size={14} /></button
						>
					{:else}
						<button
							class="send-button"
							onclick={() => sendMessage()}
							disabled={!inputValue.trim()}
							aria-label="Send message"><Send size={16} /></button
						>
					{/if}
				</div>
			</footer>
		</div>
	{/if}
</div>

<style>
	@keyframes widget-pulse {
		0%,
		100% {
			transform: scale(1);
			opacity: 0.5;
		}
		50% {
			transform: scale(1.28);
			opacity: 0;
		}
	}

	@keyframes widget-dot {
		0%,
		60%,
		100% {
			transform: translateY(0);
			opacity: 0.45;
		}
		30% {
			transform: translateY(-4px);
			opacity: 1;
		}
	}

	:host,
	.widget-shell {
		font-family: var(
			--genai-widget-font,
			-apple-system,
			BlinkMacSystemFont,
			'Segoe UI',
			sans-serif
		);
	}

	* {
		box-sizing: border-box;
	}
	button,
	textarea {
		font: inherit;
	}
	.sr-only {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
		border: 0;
	}

	.widget-shell {
		position: fixed;
		z-index: 2147483646;
		right: 16px;
		bottom: 16px;
		width: 68px;
		height: 68px;
		color: #111827;
		--message-size: 13px;
	}

	.widget-shell.left {
		right: auto;
		left: 16px;
	}
	.widget-shell.open {
		width: min(400px, calc(100vw - 32px));
		height: min(640px, calc(100vh - 32px));
	}
	.widget-shell.error {
		width: 300px;
		height: auto;
	}

	.launcher {
		position: absolute;
		right: 0;
		bottom: 0;
		width: 64px;
		height: 64px;
		border: 0;
		border-radius: 999px;
		background:
			radial-gradient(circle at 32% 22%, rgba(255, 255, 255, 0.28), transparent 36%),
			linear-gradient(
				145deg,
				color-mix(in srgb, var(--widget-primary) 90%, #fff 10%),
				color-mix(in srgb, var(--widget-primary) 86%, #000 14%)
			);
		color: #fff;
		cursor: pointer;
		display: grid;
		place-items: center;
		box-shadow:
			0 18px 38px rgba(15, 23, 42, 0.24),
			0 6px 14px rgba(15, 23, 42, 0.16);
		transition:
			transform 0.16s ease,
			box-shadow 0.16s ease;
	}

	.launcher:hover {
		transform: translateY(-2px) scale(1.03);
	}
	.launcher:focus-visible,
	.close-button:focus-visible,
	.header-button:focus-visible,
	.send-button:focus-visible,
	.mic-button:focus-visible,
	.a11y-stepper button:focus-visible,
	.a11y-toggle input:focus-visible,
	.quick-reply:focus-visible,
	.retry-button:focus-visible {
		outline: 3px solid color-mix(in srgb, var(--widget-primary) 30%, #fff 70%);
		outline-offset: 3px;
	}

	.launcher-image {
		width: 38px;
		height: 38px;
		border-radius: 999px;
		object-fit: cover;
	}
	.launcher-pulse {
		position: absolute;
		inset: -5px;
		border: 1px solid var(--widget-primary);
		border-radius: inherit;
		animation: widget-pulse 2.2s ease-out infinite;
		pointer-events: none;
	}
	.badge {
		position: absolute;
		top: 5px;
		right: 5px;
		width: 15px;
		height: 15px;
		border-radius: 999px;
		background: #ef4444;
		border: 2px solid #fff;
		box-shadow: 0 4px 10px rgba(239, 68, 68, 0.35);
	}

	.panel {
		position: absolute;
		inset: 0;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		border: 1px solid rgba(15, 23, 42, 0.12);
		background: var(--widget-bg);
		border-radius: var(--widget-radius);
		box-shadow:
			0 28px 70px rgba(15, 23, 42, 0.3),
			0 10px 26px rgba(15, 23, 42, 0.18);
	}

	.header {
		flex-shrink: 0;
		padding: 16px 16px 14px;
		background:
			radial-gradient(circle at 0% 0%, rgba(255, 255, 255, 0.22), transparent 32%),
			linear-gradient(
				135deg,
				color-mix(in srgb, var(--widget-primary) 94%, #fff 6%),
				color-mix(in srgb, var(--widget-primary) 82%, #000 18%)
			);
		color: #fff;
	}

	.header-row {
		display: flex;
		align-items: center;
		gap: 12px;
	}
	.avatar {
		width: 42px;
		height: 42px;
		border-radius: 16px;
		display: grid;
		place-items: center;
		flex-shrink: 0;
		background: rgba(255, 255, 255, 0.18);
		border: 1px solid rgba(255, 255, 255, 0.22);
		color: #fff;
		font-size: 13px;
		font-weight: 700;
		overflow: hidden;
	}
	.avatar.small {
		width: 27px;
		height: 27px;
		border-radius: 10px;
		background: color-mix(in srgb, var(--widget-primary) 12%, #fff 88%);
		color: var(--widget-primary);
		font-size: 10px;
	}
	.avatar img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}
	.title-wrap {
		min-width: 0;
		flex: 1;
	}
	.title {
		font-size: 15px;
		line-height: 20px;
		font-weight: 700;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.subtitle {
		margin-top: 1px;
		font-size: 12px;
		line-height: 16px;
		font-weight: 500;
		color: rgba(255, 255, 255, 0.76);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.header-button,
	.close-button {
		width: 32px;
		height: 32px;
		border: 0;
		border-radius: 8px;
		display: grid;
		place-items: center;
		flex-shrink: 0;
		background: rgba(255, 255, 255, 0.12);
		color: rgba(255, 255, 255, 0.82);
		cursor: pointer;
		transition: background 0.14s ease, color 0.14s ease;
	}
	.header-button:hover,
	.close-button:hover {
		background: rgba(255, 255, 255, 0.22);
		color: #fff;
	}
	.header-button.active {
		background: rgba(255, 255, 255, 0.26);
		color: #fff;
	}

	.a11y-panel {
		margin-top: 10px;
		padding: 4px;
		border: 1px solid rgba(255, 255, 255, 0.16);
		border-radius: 12px;
		background: rgba(0, 0, 0, 0.18);
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.a11y-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		padding: 7px 10px;
		border-radius: 8px;
	}
	.a11y-row:hover {
		background: rgba(255, 255, 255, 0.08);
	}
	.a11y-label {
		font-size: 12px;
		font-weight: 500;
		color: rgba(255, 255, 255, 0.9);
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.a11y-label em {
		font-style: normal;
		font-size: 10px;
		color: rgba(255, 255, 255, 0.54);
	}
	.a11y-stepper {
		display: inline-flex;
		border-radius: 6px;
		overflow: hidden;
		border: 1px solid rgba(255, 255, 255, 0.2);
	}
	.a11y-stepper button {
		min-width: 34px;
		height: 26px;
		border: 0;
		background: rgba(255, 255, 255, 0.1);
		color: #fff;
		font-size: 11px;
		font-weight: 700;
		cursor: pointer;
	}
	.a11y-stepper button + button {
		border-left: 1px solid rgba(255, 255, 255, 0.2);
	}
	.a11y-stepper button:disabled {
		opacity: 0.35;
		cursor: default;
	}
	.a11y-stepper button:not(:disabled):hover {
		background: rgba(255, 255, 255, 0.2);
	}
	.a11y-toggle {
		cursor: pointer;
	}
	.a11y-toggle input[type='checkbox'] {
		width: 34px;
		height: 18px;
		cursor: pointer;
		accent-color: rgba(255, 255, 255, 0.9);
	}

	.messages {
		flex: 1;
		overflow-y: auto;
		padding: 18px 16px;
		background: linear-gradient(
			180deg,
			color-mix(in srgb, var(--widget-bg) 94%, #fff 6%),
			var(--widget-bg)
		);
		scroll-behavior: smooth;
	}
	.messages:focus-visible {
		outline: 3px solid color-mix(in srgb, var(--widget-primary) 24%, #fff 76%);
		outline-offset: -5px;
	}
	.message-row {
		display: flex;
		gap: 9px;
		align-items: flex-end;
		margin-bottom: 12px;
	}
	.message-row.user {
		justify-content: flex-end;
	}
	.bubble {
		max-width: 82%;
		padding: 10px 12px;
		border-radius: 17px;
		font-size: var(--message-size);
		line-height: 1.48;
		word-break: break-word;
	}
	.rich-message {
		white-space: normal;
	}
	.rich-message :global(p) {
		margin: 0 0 0.72em;
	}
	.rich-message :global(p:last-child),
	.rich-message :global(ul:last-child),
	.rich-message :global(ol:last-child),
	.rich-message :global(h3:last-child),
	.rich-message :global(h4:last-child) {
		margin-bottom: 0;
	}
	.rich-message :global(ul),
	.rich-message :global(ol) {
		margin: 0.35em 0 0.8em;
		padding-left: 1.2em;
	}
	.rich-message :global(li) {
		margin: 0.22em 0;
		padding-left: 0.1em;
	}
	.rich-message :global(strong) {
		font-weight: 750;
	}
	.rich-message :global(em) {
		font-style: italic;
	}
	.rich-message :global(code) {
		border-radius: 6px;
		background: rgba(15, 23, 42, 0.07);
		padding: 0.1em 0.34em;
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 0.92em;
	}
	.rich-message :global(a) {
		color: inherit;
		font-weight: 700;
		text-decoration: underline;
		text-underline-offset: 2px;
	}
	.rich-message :global(h3),
	.rich-message :global(h4) {
		margin: 0.1em 0 0.45em;
		font-size: 1em;
		line-height: 1.35;
		font-weight: 800;
	}
	.bubble.assistant {
		border-bottom-left-radius: 6px;
		background: #fff;
		color: #111827;
		border: 1px solid rgba(15, 23, 42, 0.08);
		box-shadow: 0 5px 16px rgba(15, 23, 42, 0.06);
	}
	.bubble.user {
		border-bottom-right-radius: 6px;
		background: var(--widget-primary);
		color: #fff;
		box-shadow: 0 6px 16px color-mix(in srgb, var(--widget-primary) 28%, transparent);
	}
	.bubble.error {
		background: #fff7ed;
		border-color: rgba(234, 88, 12, 0.2);
		color: #7c2d12;
	}
	.typing {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		min-width: 38px;
		height: 18px;
	}
	.typing span {
		width: 6px;
		height: 6px;
		border-radius: 999px;
		background: #9ca3af;
		animation: widget-dot 1.1s infinite;
	}
	.typing span:nth-child(2) {
		animation-delay: 130ms;
	}
	.typing span:nth-child(3) {
		animation-delay: 260ms;
	}
	.quick-replies {
		display: flex;
		flex-wrap: wrap;
		gap: 7px;
		margin: 3px 0 12px 36px;
	}
	.quick-reply {
		border: 1px solid color-mix(in srgb, var(--widget-primary) 35%, transparent);
		background: color-mix(in srgb, var(--widget-primary) 7%, #fff 93%);
		color: color-mix(in srgb, var(--widget-primary) 82%, #111827 18%);
		border-radius: 999px;
		padding: 7px 11px;
		font-size: 12px;
		line-height: 15px;
		cursor: pointer;
	}
	.retry-button {
		margin-top: 8px;
		border: 0;
		border-radius: 999px;
		background: #fed7aa;
		color: #7c2d12;
		padding: 6px 10px;
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-size: 12px;
		font-weight: 600;
		cursor: pointer;
	}

	.composer {
		flex-shrink: 0;
		padding: 12px;
		border-top: 1px solid rgba(15, 23, 42, 0.08);
		background: rgba(255, 255, 255, 0.82);
		backdrop-filter: blur(12px);
	}
	.voice-status {
		margin: 0 2px 8px;
		font-size: 11px;
		line-height: 15px;
		color: #64748b;
	}
	.composer-inner {
		display: flex;
		align-items: flex-end;
		gap: 8px;
		border: 1px solid rgba(15, 23, 42, 0.1);
		border-radius: 22px;
		background: #fff;
		padding: 7px 7px 7px 13px;
		box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
	}
	textarea {
		flex: 1;
		min-height: 22px;
		max-height: 96px;
		resize: none;
		border: 0;
		outline: 0;
		background: transparent;
		color: #111827;
		font-size: 13px;
		line-height: 20px;
		padding: 6px 0;
		overflow-y: auto;
	}
	textarea::placeholder {
		color: #8b97a8;
	}
	.mic-button,
	.send-button {
		width: 34px;
		height: 34px;
		border: 0;
		border-radius: 999px;
		display: grid;
		place-items: center;
		flex-shrink: 0;
		background: var(--widget-primary);
		color: #fff;
		cursor: pointer;
	}
	.mic-button {
		background: #f8fafc;
		color: #475569;
		border: 1px solid rgba(15, 23, 42, 0.08);
	}
	.mic-button.listening {
		background: #fee2e2;
		color: #b91c1c;
		box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.12);
	}
	.mic-button:disabled {
		cursor: default;
		opacity: 0.42;
	}
	.send-button:disabled {
		cursor: default;
		opacity: 0.42;
	}
	.state-error {
		position: absolute;
		right: 0;
		bottom: 0;
		width: 300px;
		border-radius: 18px;
		padding: 14px;
		background: #fff;
		color: #7f1d1d;
		box-shadow: 0 16px 34px rgba(15, 23, 42, 0.16);
	}
	.state-error strong {
		display: block;
		margin-bottom: 4px;
		font-size: 13px;
		color: #111827;
	}
	.state-error p {
		font-size: 12px;
		line-height: 17px;
		margin: 0;
	}

	.widget-shell.text-large {
		--message-size: 15px;
	}
	.widget-shell.text-largest {
		--message-size: 17px;
	}
	.widget-shell.text-large .title,
	.widget-shell.text-largest .title {
		font-size: 17px;
		line-height: 22px;
	}
	.widget-shell.text-large textarea,
	.widget-shell.text-large .quick-reply {
		font-size: 14px;
	}
	.widget-shell.text-largest textarea,
	.widget-shell.text-largest .quick-reply {
		font-size: 16px;
	}
	.widget-shell.high-contrast .panel {
		border-color: #000;
		box-shadow: 0 0 0 2px #000;
	}
	.widget-shell.high-contrast .header {
		background: #000;
	}
	.widget-shell.high-contrast .bubble.assistant,
	.widget-shell.high-contrast .composer-inner {
		border-color: #000;
	}
	.widget-shell.high-contrast .bubble.user,
	.widget-shell.high-contrast .send-button {
		background: #000;
		box-shadow: none;
	}
	.widget-shell.high-contrast .messages {
		background: #fff;
	}
	.widget-shell.screen-reader-mode .launcher-pulse,
	.widget-shell.screen-reader-mode .badge {
		display: none;
	}
	.widget-shell.screen-reader-mode .messages {
		scroll-behavior: auto;
	}
	.widget-shell.reduce-motion *,
	.widget-shell.screen-reader-mode * {
		animation: none !important;
		transition: none !important;
		scroll-behavior: auto !important;
	}

	@media (prefers-reduced-motion: reduce) {
		.widget-shell *,
		.widget-shell {
			animation: none !important;
			transition: none !important;
			scroll-behavior: auto !important;
		}
	}

	@media (max-width: 640px) {
		.widget-shell.open.mobile-fullscreen {
			inset: 0;
			width: 100vw;
			height: 100vh;
		}
		.widget-shell.open.mobile-fullscreen .panel {
			border-radius: 0;
			border: 0;
		}
	}
</style>
