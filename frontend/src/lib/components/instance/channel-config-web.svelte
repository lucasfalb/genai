<script lang="ts">
	import * as Accordion from '$lib/components/ui/accordion/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import * as Command from '$lib/components/ui/command/index.js';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import Copy from '@lucide/svelte/icons/copy';
	import Plus from '@lucide/svelte/icons/plus';
	import X from '@lucide/svelte/icons/x';
	import Upload from '@lucide/svelte/icons/upload';
	import Check from '@lucide/svelte/icons/check';
	import ChevronsUpDown from '@lucide/svelte/icons/chevrons-up-down';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import MessageCircle from '@lucide/svelte/icons/message-circle';
	import * as LucideIcons from '@lucide/svelte/icons';
	import { GOOGLE_FONT_FAMILIES } from '$lib/data/g-fonts';
	import { widgetDefaultMessages, getLocaleMessages } from '$lib/data/widget-locales';
	import type { UiMessageKey, UiMessages } from '$lib/data/widget-locales';
	import { toast } from 'svelte-sonner';
	import type { WebWidgetConfig } from '$lib/api/types';
	import { defaultWebWidgetConfig } from '$lib/api/types';
	import { instancesApi } from '$lib/api/instances';
	import { cn } from '$lib/utils';

	let {
		instanceId,
		tenantId = '',
		config = defaultWebWidgetConfig(),
		allowedDomains = '',
		onchange
	}: {
		instanceId: string;
		tenantId?: string;
		config?: WebWidgetConfig;
		allowedDomains?: string;
		onchange?: (cfg: WebWidgetConfig, domains: string) => void;
	} = $props();

	const localeOptions = [
		{ value: 'en-US', label: 'English (US)' },
		{ value: 'en-GB', label: 'English (UK)' },
		{ value: 'pt-PT', label: 'Portuguese (Portugal)' },
		{ value: 'pt-BR', label: 'Portuguese (Brazil)' },
		{ value: 'es-ES', label: 'Spanish' },
		{ value: 'fr-FR', label: 'French' },
		{ value: 'de-DE', label: 'German' },
		{ value: 'it-IT', label: 'Italian' }
	];
	const uiMessageFields = [
		{ key: 'default_opening_message', label: 'Default opening message' },
		{ key: 'input_placeholder', label: 'Input placeholder' },
		{ key: 'waiting_placeholder', label: 'Waiting placeholder' },
		{ key: 'listening', label: 'Listening status' },
		{ key: 'voice_ready', label: 'Voice ready status' },
		{ key: 'voice_unsupported', label: 'Voice unsupported status' },
		{ key: 'voice_permission_blocked', label: 'Microphone blocked status' },
		{ key: 'use_microphone', label: 'Microphone button' },
		{ key: 'stop_microphone', label: 'Stop microphone button' },
		{ key: 'accessibility_controls', label: 'Accessibility button label' },
		{ key: 'message_failed', label: 'Message failed' },
		{ key: 'no_response', label: 'No response' },
		{ key: 'retry_message', label: 'Retry button' }
	] as const;

	const widgetDefaults = defaultWebWidgetConfig();
	let cfg = $state<WebWidgetConfig>({
		...widgetDefaults,
		...config,
		ui_messages: normalizeUiMessages(config.ui_messages ?? widgetDefaults.ui_messages)
	});
	let domains = $state(allowedDomains);
	let newReply = $state('');
	let openSections = $state<string[]>(['appearance']);
	let uploadingAvatar = $state(false);
	let uploadingLauncher = $state(false);
	let avatarIconOpen = $state(false);
	let launcherIconOpen = $state(false);
	let avatarIconSearch = $state('');
	let avatarIconPage = $state(0);
	let launcherIconSearch = $state('');
	let launcherIconPage = $state(0);
	let autoOpenDelayValue = $state(
		cfg.auto_open_delay === null ? 'off' : String(cfg.auto_open_delay)
	);
	let copyLocale = $state(cfg.locale);

	const STATIC_FONT_OPTIONS = [
		{ value: 'inherit', label: 'Inherit from page' },
		{ value: 'system', label: 'System UI' }
	];

	let fontOpen = $state(false);

	const autoOpenDelayOptions = [
		{ value: 'off', label: 'Disabled' },
		{ value: '3', label: 'After 3 seconds' },
		{ value: '5', label: 'After 5 seconds' },
		{ value: '10', label: 'After 10 seconds' },
		{ value: '30', label: 'After 30 seconds' }
	];

	function isMessageKey(value: string): value is UiMessageKey {
		return value in widgetDefaultMessages;
	}

	function defaultMessagesForLocale(locale: string): UiMessages {
		return { ...widgetDefaultMessages, ...getLocaleMessages(locale) };
	}

	function normalizeUiMessages(
		messages: WebWidgetConfig['ui_messages'] | undefined
	): Record<string, UiMessages> {
		const normalized = Object.fromEntries(
			localeOptions.map((option) => [option.value, defaultMessagesForLocale(option.value)])
		) as Record<string, UiMessages>;
		if (!messages) return normalized;

		const flatMessages: Partial<UiMessages> = {};
		for (const [key, value] of Object.entries(messages)) {
			if (typeof value === 'string' && isMessageKey(key)) {
				flatMessages[key] = value;
			} else if (value && typeof value === 'object') {
				normalized[key] = {
					...defaultMessagesForLocale(key),
					...(value as Partial<UiMessages>)
				};
			}
		}
		if (Object.keys(flatMessages).length > 0) {
			normalized[config.locale || widgetDefaults.locale] = {
				...defaultMessagesForLocale(config.locale || widgetDefaults.locale),
				...flatMessages
			};
		}
		return normalized;
	}

	function localeCopy(locale: string): UiMessages {
		const messages = cfg.ui_messages[locale];
		if (messages && typeof messages === 'object') return messages as UiMessages;
		const defaults = defaultMessagesForLocale(locale);
		cfg.ui_messages = { ...cfg.ui_messages, [locale]: defaults };
		return defaults;
	}

	function updateLocaleCopy(locale: string, key: UiMessageKey, value: string) {
		cfg.ui_messages = {
			...cfg.ui_messages,
			[locale]: {
				...localeCopy(locale),
				[key]: value
			}
		};
	}

	function resetLocaleCopy(locale: string) {
		cfg.ui_messages = {
			...cfg.ui_messages,
			[locale]: defaultMessagesForLocale(locale)
		};
		toast.success(`Reset ${localeOptions.find((o) => o.value === locale)?.label ?? locale} copy.`);
	}

	function applyLocale(locale: string) {
		cfg.locale = locale;
		copyLocale = locale;
	}

	function configForSave(config: WebWidgetConfig): WebWidgetConfig {
		const { logo_url: _logoUrl, persist_conversation: _persistConversation, ...next } = config as WebWidgetConfig & {
			logo_url?: unknown;
			persist_conversation?: unknown;
		};
		return next as WebWidgetConfig;
	}

	function pascalToKebab(value: string) {
		return value.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase();
	}

	function kebabToPascal(value: string) {
		return value
			.split('-')
			.map((part) => part.charAt(0).toUpperCase() + part.slice(1))
			.join('');
	}

	function iconLabel(value: string) {
		return value
			.split('-')
			.map((part) => part.charAt(0).toUpperCase() + part.slice(1))
			.join(' ');
	}

	type LucideIcon = typeof MessageCircle;
	const iconRegistry = LucideIcons as unknown as Record<string, LucideIcon>;

	const lucideIconOptions = (() => {
		const seen = new Set<string>();
		return Object.keys(LucideIcons)
			.filter((name) => /^[A-Z]/.test(name))
			.sort()
			.flatMap((name) => {
				const value = pascalToKebab(name);
				if (seen.has(value)) return [];
				seen.add(value);
				return [{ value, label: iconLabel(value), Icon: iconRegistry[name] }];
			});
	})();

	function getLucideIcon(value: string | null | undefined) {
		const name = kebabToPascal(value || '');
		return iconRegistry[name] ?? MessageCircle;
	}

	const ICONS_PER_PAGE = 48;

	const filteredAvatarIcons = $derived(
		avatarIconSearch.trim()
			? lucideIconOptions.filter((i) =>
					i.label.toLowerCase().includes(avatarIconSearch.toLowerCase())
				)
			: lucideIconOptions
	);
	const avatarTotalPages = $derived(Math.ceil(filteredAvatarIcons.length / ICONS_PER_PAGE));
	const avatarPageIcons = $derived(
		filteredAvatarIcons.slice(
			avatarIconPage * ICONS_PER_PAGE,
			(avatarIconPage + 1) * ICONS_PER_PAGE
		)
	);

	const filteredLauncherIcons = $derived(
		launcherIconSearch.trim()
			? lucideIconOptions.filter((i) =>
					i.label.toLowerCase().includes(launcherIconSearch.toLowerCase())
				)
			: lucideIconOptions
	);
	const launcherTotalPages = $derived(Math.ceil(filteredLauncherIcons.length / ICONS_PER_PAGE));
	const launcherPageIcons = $derived(
		filteredLauncherIcons.slice(
			launcherIconPage * ICONS_PER_PAGE,
			(launcherIconPage + 1) * ICONS_PER_PAGE
		)
	);

	$effect(() => {
		avatarIconSearch;
		avatarIconPage = 0;
	});

	$effect(() => {
		launcherIconSearch;
		launcherIconPage = 0;
	});

	const selectedFontLabel = $derived(
		STATIC_FONT_OPTIONS.find((o) => o.value === cfg.font_family)?.label ??
			cfg.font_family ??
			'System UI'
	);
	const selectedAutoOpenDelayLabel = $derived(
		autoOpenDelayOptions.find((option) => option.value === autoOpenDelayValue)?.label ?? 'Disabled'
	);
	const selectedAvatarIconLabel = $derived(iconLabel(cfg.avatar_icon || 'bot'));
	const selectedLauncherIconLabel = $derived(iconLabel(cfg.launcher_icon || 'message-circle'));
	const SelectedLauncherIcon = $derived(getLucideIcon(cfg.launcher_icon));

	$effect(() => {
		const font = cfg.font_family;
		if (font && font !== 'inherit' && font !== 'system' && typeof document !== 'undefined') {
			const id = `gf-${font.replace(/\s+/g, '-').toLowerCase()}`;
			if (!document.getElementById(id)) {
				const link = document.createElement('link');
				link.id = id;
				link.rel = 'stylesheet';
				link.href = `https://fonts.googleapis.com/css2?family=${encodeURIComponent(font)}:wght@400;500;600&display=swap`;
				document.head.appendChild(link);
			}
		}
	});

	$effect(() => {
		onchange?.(configForSave(cfg), domains);
	});

	$effect(() => {
		cfg.auto_open_delay = autoOpenDelayValue === 'off' ? null : Number(autoOpenDelayValue);
	});

	const widgetOrigin =
		typeof window !== 'undefined' ? window.location.origin : 'https://your-domain.com';
	const snippet = $derived(
		`<script src="${widgetOrigin}/widget.js" data-instance="${instanceId}"><\/script>`
	);

	function copySnippet() {
		navigator.clipboard.writeText(snippet);
		toast.success('Snippet copied.');
	}

	function addReply() {
		const val = newReply.trim();
		if (!val || cfg.quick_replies.length >= 4) return;
		cfg.quick_replies = [...cfg.quick_replies, val];
		newReply = '';
	}

	function removeReply(i: number) {
		cfg.quick_replies = cfg.quick_replies.filter((_, idx) => idx !== i);
	}

	function handleReplyKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			addReply();
		}
	}

	async function uploadImage(field: 'avatar_image_url' | 'launcher_image_url', file: File) {
		if (field === 'avatar_image_url') uploadingAvatar = true;
		else uploadingLauncher = true;
		try {
			const { url } = await instancesApi.uploadChannelImage(instanceId, file);
			if (field === 'avatar_image_url') cfg.avatar_image_url = url;
			else cfg.launcher_image_url = url;
		} catch {
			toast.error('Image upload failed.');
		} finally {
			if (field === 'avatar_image_url') uploadingAvatar = false;
			else uploadingLauncher = false;
		}
	}

	function triggerFileInput(field: 'avatar_image_url' | 'launcher_image_url') {
		const input = document.createElement('input');
		input.type = 'file';
		input.accept = 'image/png,image/jpeg,image/webp,image/svg+xml';
		input.onchange = (e) => {
			const file = (e.target as HTMLInputElement).files?.[0];
			if (file) uploadImage(field, file);
		};
		input.click();
	}

	function activeChoiceStyle(selected: boolean) {
		return selected
			? 'background:color-mix(in srgb, var(--text-main) 10%, transparent);color:var(--text-main);border-color:var(--text-main)'
			: 'background:transparent;color:var(--text-main);border-color:var(--ds-border)';
	}

	let frameworkDialogOpen = $state(false);
	let activeFrameworkId = $state<string | null>(null);

	type Framework = {
		id: string;
		name: string;
		description: string;
		icon: string;
		color: string;
		code: string;
	};

	const frameworks = $derived.by<Framework[]>(() => [
		{
			id: 'html',
			name: 'Plain HTML',
			description: 'Any static page or HTML file',
			icon: 'file-code-2',
			color: '#E44D26',
			code: `<!-- Paste before </body> -->\n${snippet}`
		},
		{
			id: 'react',
			name: 'React',
			description: 'Create React App, Vite, Remix',
			icon: 'atom',
			color: '#61DAFB',
			code: `import { useEffect } from 'react';\n\nexport function ChatWidget() {\n  useEffect(() => {\n    const s = document.createElement('script');\n    s.src = '${widgetOrigin}/widget.js';\n    s.dataset.instance = '${instanceId}';\n    document.body.appendChild(s);\n    return () => s.remove();\n  }, []);\n  return null;\n}`
		},
		{
			id: 'nextjs',
			name: 'Next.js',
			description: 'App Router or Pages Router',
			icon: 'layers',
			color: '#aaaaaa',
			code: `// app/layout.tsx\nexport default function RootLayout({ children }: { children: React.ReactNode }) {\n  return (\n    <html>\n      <body>\n        {children}\n        <script src="${widgetOrigin}/widget.js" data-instance="${instanceId}" async />\n      </body>\n    </html>\n  );\n}`
		},
		{
			id: 'vue',
			name: 'Vue.js',
			description: 'Vue 3, Nuxt',
			icon: 'component',
			color: '#4FC08D',
			code: `<script setup>\nimport { onMounted, onUnmounted } from 'vue';\nlet script;\nonMounted(() => {\n  script = document.createElement('script');\n  script.src = '${widgetOrigin}/widget.js';\n  script.dataset.instance = '${instanceId}';\n  document.body.appendChild(script);\n});\nonUnmounted(() => script?.remove());\n<\/script>`
		},
		{
			id: 'svelte',
			name: 'Svelte / SvelteKit',
			description: 'SvelteKit, Svelte 5',
			icon: 'zap',
			color: '#FF3E00',
			code: `<!-- +layout.svelte -->\n<script>\n  import { onMount } from 'svelte';\n  onMount(() => {\n    const s = document.createElement('script');\n    s.src = '${widgetOrigin}/widget.js';\n    s.dataset.instance = '${instanceId}';\n    document.body.appendChild(s);\n    return () => s.remove();\n  });\n<\/script>\n<slot />`
		},
		{
			id: 'angular',
			name: 'Angular',
			description: 'Angular 16+',
			icon: 'shield',
			color: '#DD0031',
			code: `// app.component.ts\nimport { Component, OnInit, OnDestroy } from '@angular/core';\n\n@Component({ selector: 'app-root', template: '<router-outlet />' })\nexport class AppComponent implements OnInit, OnDestroy {\n  private script?: HTMLScriptElement;\n\n  ngOnInit() {\n    this.script = document.createElement('script');\n    this.script.src = '${widgetOrigin}/widget.js';\n    this.script.dataset['instance'] = '${instanceId}';\n    document.body.appendChild(this.script);\n  }\n\n  ngOnDestroy() { this.script?.remove(); }\n}`
		}
	]);

	const activeFramework = $derived(
		activeFrameworkId ? (frameworks.find((f) => f.id === activeFrameworkId) ?? null) : null
	);
</script>

<Accordion.Root type="multiple" bind:value={openSections} class="w-full">
	<!-- 1. Appearance -->
	<Accordion.Item value="appearance">
		<Accordion.Trigger class="px-1 hover:no-underline">
			<span class="flex items-center gap-2 text-sm font-medium" style="color:var(--text-main)">
				Appearance
				<span class="text-[11px] font-normal text-muted-foreground">Colors, typography, layout</span
				>
			</span>
		</Accordion.Trigger>
		<Accordion.Content class="px-1">
			<div class="space-y-4 pb-2">
				<div class="grid gap-3 sm:grid-cols-2">
					<div class="space-y-1.5">
						<label class="field-label">Primary color</label>
						<div class="flex items-center gap-2">
							<input
								type="color"
								bind:value={cfg.primary_color}
								class="h-9 w-12 cursor-pointer rounded border bg-transparent p-1"
								style="border-color:var(--ds-border)"
							/>
							<Input
								bind:value={cfg.primary_color}
								class="font-mono text-xs"
								placeholder="#3b82f6"
							/>
						</div>
					</div>
					<div class="space-y-1.5">
						<label class="field-label">Background color</label>
						<div class="flex items-center gap-2">
							<input
								type="color"
								bind:value={cfg.bg_color}
								class="h-9 w-12 cursor-pointer rounded border bg-transparent p-1"
								style="border-color:var(--ds-border)"
							/>
							<Input bind:value={cfg.bg_color} class="font-mono text-xs" placeholder="#ffffff" />
						</div>
					</div>
				</div>

				<div class="space-y-1.5">
					<label class="field-label">Border radius</label>
					<div class="flex gap-1.5">
						{#each ['sharp', 'rounded', 'full'] as const as opt}
							<button
								onclick={() => (cfg.border_radius = opt)}
								class="flex-1 rounded border px-3 py-1.5 text-xs transition-colors"
								style={activeChoiceStyle(cfg.border_radius === opt)}
							>
								{opt.charAt(0).toUpperCase() + opt.slice(1)}
							</button>
						{/each}
					</div>
				</div>

				<div class="space-y-1.5">
					<label class="field-label">Widget position</label>
					<div class="flex gap-1.5">
						{#each ['bottom-right', 'bottom-left'] as const as pos}
							<button
								onclick={() => (cfg.position = pos)}
								class="flex-1 rounded border px-3 py-1.5 text-xs transition-colors"
								style={activeChoiceStyle(cfg.position === pos)}
							>
								{pos === 'bottom-right' ? 'Bottom right' : 'Bottom left'}
							</button>
						{/each}
					</div>
				</div>

				<div class="space-y-1.5">
					<label class="field-label">Font family</label>
					<Popover.Root bind:open={fontOpen}>
						<Popover.Trigger class="w-full">
							<button
								type="button"
								role="combobox"
								aria-expanded={fontOpen}
								class="flex h-9 w-full items-center justify-between rounded-md border px-3 py-2 text-sm"
								style="border-color:var(--ds-border);background:var(--surface)"
							>
								<span class="truncate">{selectedFontLabel}</span>
								<ChevronsUpDown class="ml-2 size-3.5 shrink-0 text-muted-foreground" />
							</button>
						</Popover.Trigger>
						<Popover.Content class="w-55 p-0">
							<Command.Root>
								<Command.Input placeholder="Search fonts…" />
								<Command.List class="max-h-60 overflow-y-auto">
									<Command.Empty>No font found.</Command.Empty>
									<Command.Group heading="Default">
										{#each STATIC_FONT_OPTIONS as option (option.value)}
											<Command.Item
												value={option.value}
												onSelect={() => {
													cfg.font_family = option.value;
													fontOpen = false;
												}}
											>
												<Check
													class={[
														'mr-2 size-3.5',
														cfg.font_family === option.value ? 'opacity-100' : 'opacity-0'
													]}
												/>
												{option.label}
											</Command.Item>
										{/each}
									</Command.Group>
									<Command.Group heading="Google Fonts">
										{#each GOOGLE_FONT_FAMILIES as family (family)}
											<Command.Item
												value={family}
												onSelect={() => {
													cfg.font_family = family;
													fontOpen = false;
												}}
											>
												<Check
													class={[
														'mr-2 size-3.5',
														cfg.font_family === family ? 'opacity-100' : 'opacity-0'
													]}
												/>
												{family}
											</Command.Item>
										{/each}
									</Command.Group>
								</Command.List>
							</Command.Root>
						</Popover.Content>
					</Popover.Root>
				</div>
			</div>
		</Accordion.Content>
	</Accordion.Item>

	<!-- 2. Identity -->
	<Accordion.Item value="identity">
		<Accordion.Trigger class="px-1 hover:no-underline">
			<span class="flex items-center gap-2 text-sm font-medium" style="color:var(--text-main)">
				Identity
				<span class="text-[11px] font-normal text-muted-foreground">Name, branding, avatar</span>
			</span>
		</Accordion.Trigger>
		<Accordion.Content class="px-1">
			<div class="space-y-4 pb-2">
				<div class="grid gap-3 sm:grid-cols-2">
					<div class="space-y-1.5">
						<label class="field-label">Widget title</label>
						<Input bind:value={cfg.title} placeholder="Chat with us" />
					</div>
					<div class="space-y-1.5">
						<label class="field-label">Subtitle / tagline</label>
						<Input bind:value={cfg.subtitle} placeholder="We typically reply in a few minutes" />
					</div>
				</div>

				<div class="space-y-1.5">
					<label class="field-label">Bot display name</label>
					<Input bind:value={cfg.bot_name} placeholder="Assistant" />
				</div>

				<div class="space-y-1.5">
					<p class="field-label">Bot avatar</p>
					<p class="text-[11px] text-muted-foreground">
						Profile picture shown next to each bot message
					</p>
					<div class="flex gap-1.5">
						{#each ['initials', 'icon', 'image'] as const as mode}
							<button
								onclick={() => (cfg.avatar_mode = mode)}
								class="flex-1 rounded border px-3 py-1.5 text-xs capitalize transition-colors"
								style={activeChoiceStyle(cfg.avatar_mode === mode)}
							>
								{mode === 'initials'
									? 'Auto initials'
									: mode === 'icon'
										? 'Lucide icon'
										: 'Custom image'}
							</button>
						{/each}
					</div>
					{#if cfg.avatar_mode === 'icon'}
						{@const AvatarIcon = getLucideIcon(cfg.avatar_icon)}
						<Popover.Root bind:open={avatarIconOpen}>
							<Popover.Trigger>
								{#snippet child({ props })}
									<Button
										{...props}
										variant="outline"
										class="mt-2 h-10 w-full justify-between"
										role="combobox"
										aria-expanded={avatarIconOpen}
									>
										<span class="flex min-w-0 items-center gap-2">
											<AvatarIcon class="size-4 shrink-0" />
											<span class="truncate">{selectedAvatarIconLabel}</span>
										</span>
										<ChevronsUpDown class="size-4 shrink-0 opacity-50" />
									</Button>
								{/snippet}
							</Popover.Trigger>
							<Popover.Content class="w-[320px] p-3">
								<Input
									bind:value={avatarIconSearch}
									placeholder="Search icons…"
									class="mb-2 h-8 text-xs"
								/>
								{#if avatarPageIcons.length > 0}
									<div class="grid grid-cols-8 gap-0.5">
										{#each avatarPageIcons as icon (icon.value)}
											<button
												title={icon.label}
												onclick={() => {
													cfg.avatar_icon = icon.value;
													avatarIconOpen = false;
												}}
												class="flex items-center justify-center rounded p-1.5 transition-colors hover:bg-accent {cfg.avatar_icon ===
												icon.value
													? 'bg-accent ring-1 ring-primary'
													: ''}"
											>
												<icon.Icon class="size-4" />
											</button>
										{/each}
									</div>
								{:else}
									<p class="py-4 text-center text-xs text-muted-foreground">No icons found.</p>
								{/if}
								{#if avatarTotalPages > 1}
									<div
										class="mt-2 flex items-center justify-between border-t pt-2"
										style="border-color:var(--ds-border)"
									>
										<Button
											variant="ghost"
											size="icon-sm"
											onclick={() => avatarIconPage--}
											disabled={avatarIconPage === 0}
										>
											<ChevronLeft class="size-3.5" />
										</Button>
										<span class="text-[11px] text-muted-foreground"
											>{avatarIconPage + 1} / {avatarTotalPages}</span
										>
										<Button
											variant="ghost"
											size="icon-sm"
											onclick={() => avatarIconPage++}
											disabled={avatarIconPage >= avatarTotalPages - 1}
										>
											<ChevronRight class="size-3.5" />
										</Button>
									</div>
								{/if}
							</Popover.Content>
						</Popover.Root>
					{:else if cfg.avatar_mode === 'image'}
						<div class="mt-2">
							{#if cfg.avatar_image_url}
								<div class="flex items-center gap-3">
									<div class="relative shrink-0">
										<img
											src={cfg.avatar_image_url}
											alt="avatar"
											class="size-14 rounded-full border-2 object-cover"
											style="border-color:var(--ds-border)"
										/>
										<button
											onclick={() => {
												cfg.avatar_image_url = null;
											}}
											class="absolute -top-1 -right-1 flex size-5 items-center justify-center rounded-full bg-destructive text-white"
											aria-label="Remove avatar"
										>
											<X class="size-3" />
										</button>
									</div>
									<div>
										<Button
											variant="outline"
											size="sm"
											onclick={() => triggerFileInput('avatar_image_url')}
											disabled={uploadingAvatar}
										>
											<Upload class="mr-1.5 size-3.5" />
											{uploadingAvatar ? 'Uploading…' : 'Change image'}
										</Button>
										<p class="mt-1 text-[11px] text-muted-foreground">
											PNG, JPEG, WebP or SVG · max 2 MB
										</p>
									</div>
								</div>
							{:else}
								<button
									onclick={() => triggerFileInput('avatar_image_url')}
									disabled={uploadingAvatar}
									class="flex h-14 w-full items-center justify-center gap-2.5 rounded-xl border-2 border-dashed text-muted-foreground transition-colors hover:border-primary hover:text-primary"
									style="border-color:var(--ds-border)"
								>
									<Upload class="size-4" />
									<span class="text-xs"
										>{uploadingAvatar ? 'Uploading…' : 'Click to upload avatar'}</span
									>
								</button>
								<p class="mt-1 text-[11px] text-muted-foreground">
									PNG, JPEG, WebP or SVG · max 2 MB
								</p>
							{/if}
						</div>
					{/if}
				</div>

			</div>
		</Accordion.Content>
	</Accordion.Item>

	<!-- 3. Launcher Button -->
	<Accordion.Item value="launcher">
		<Accordion.Trigger class="px-1 hover:no-underline">
			<span class="flex items-center gap-2 text-sm font-medium" style="color:var(--text-main)">
				Launcher button
				<span class="text-[11px] font-normal text-muted-foreground"
					>Icon, image, auto-open, badge</span
				>
			</span>
		</Accordion.Trigger>
		<Accordion.Content class="px-1">
			<div class="space-y-4 pb-2">
				<div class="space-y-1.5">
					<p class="field-label">Button type</p>
					<div class="flex gap-1.5">
						{#each [{ value: 'icon', label: 'Lucide icon' }, { value: 'image', label: 'Custom image' }] as opt}
							<button
								onclick={() => (cfg.launcher_mode = opt.value as 'icon' | 'image')}
								class="flex-1 rounded border px-3 py-1.5 text-xs transition-colors"
								style={activeChoiceStyle(cfg.launcher_mode === opt.value)}
							>
								{opt.label}
							</button>
						{/each}
					</div>

					{#if cfg.launcher_mode === 'icon'}
						<Popover.Root bind:open={launcherIconOpen}>
							<Popover.Trigger>
								{#snippet child({ props })}
									<Button
										{...props}
										variant="outline"
										class="mt-1.5 h-10 w-full justify-between"
										role="combobox"
										aria-expanded={launcherIconOpen}
									>
										<span class="flex min-w-0 items-center gap-2">
											<SelectedLauncherIcon class="size-4 shrink-0" />
											<span class="truncate">{selectedLauncherIconLabel}</span>
										</span>
										<ChevronsUpDown class="size-4 shrink-0 opacity-50" />
									</Button>
								{/snippet}
							</Popover.Trigger>
							<Popover.Content class="w-[320px] p-3">
								<Input
									bind:value={launcherIconSearch}
									placeholder="Search icons…"
									class="mb-2 h-8 text-xs"
								/>
								{#if launcherPageIcons.length > 0}
									<div class="grid grid-cols-8 gap-0.5">
										{#each launcherPageIcons as icon (icon.value)}
											<button
												title={icon.label}
												onclick={() => {
													cfg.launcher_icon = icon.value;
													launcherIconOpen = false;
												}}
												class="flex items-center justify-center rounded p-1.5 transition-colors hover:bg-accent {cfg.launcher_icon ===
												icon.value
													? 'bg-accent ring-1 ring-primary'
													: ''}"
											>
												<icon.Icon class="size-4" />
											</button>
										{/each}
									</div>
								{:else}
									<p class="py-4 text-center text-xs text-muted-foreground">No icons found.</p>
								{/if}
								{#if launcherTotalPages > 1}
									<div
										class="mt-2 flex items-center justify-between border-t pt-2"
										style="border-color:var(--ds-border)"
									>
										<Button
											variant="ghost"
											size="icon-sm"
											onclick={() => launcherIconPage--}
											disabled={launcherIconPage === 0}
										>
											<ChevronLeft class="size-3.5" />
										</Button>
										<span class="text-[11px] text-muted-foreground"
											>{launcherIconPage + 1} / {launcherTotalPages}</span
										>
										<Button
											variant="ghost"
											size="icon-sm"
											onclick={() => launcherIconPage++}
											disabled={launcherIconPage >= launcherTotalPages - 1}
										>
											<ChevronRight class="size-3.5" />
										</Button>
									</div>
								{/if}
							</Popover.Content>
						</Popover.Root>
					{:else}
						<div class="mt-1.5">
							{#if cfg.launcher_image_url}
								<div class="flex items-center gap-3">
									<div class="relative shrink-0">
										<div
											class="flex size-12 items-center justify-center overflow-hidden rounded-full border-2"
											style="border-color:var(--ds-border);background:{cfg.primary_color}"
										>
											<img
												src={cfg.launcher_image_url}
												alt="launcher"
												class="size-8 object-contain"
											/>
										</div>
										<button
											onclick={() => {
												cfg.launcher_image_url = null;
											}}
											class="absolute -top-1 -right-1 flex size-5 items-center justify-center rounded-full bg-destructive text-white"
											aria-label="Remove launcher image"
										>
											<X class="size-3" />
										</button>
									</div>
									<div>
										<Button
											variant="outline"
											size="sm"
											onclick={() => triggerFileInput('launcher_image_url')}
											disabled={uploadingLauncher}
										>
											<Upload class="mr-1.5 size-3.5" />
											{uploadingLauncher ? 'Uploading…' : 'Change image'}
										</Button>
										<p class="mt-1 text-[11px] text-muted-foreground">
											Preview uses your primary color as background
										</p>
									</div>
								</div>
							{:else}
								<button
									onclick={() => triggerFileInput('launcher_image_url')}
									disabled={uploadingLauncher}
									class="flex h-12 w-full items-center justify-center gap-2.5 rounded-xl border-2 border-dashed text-muted-foreground transition-colors hover:border-primary hover:text-primary"
									style="border-color:var(--ds-border)"
								>
									<Upload class="size-4" />
									<span class="text-xs"
										>{uploadingLauncher ? 'Uploading…' : 'Click to upload button image'}</span
									>
								</button>
								<p class="mt-1 text-[11px] text-muted-foreground">
									PNG, JPEG, WebP or SVG · max 2 MB · Square images work best
								</p>
							{/if}
						</div>
					{/if}
				</div>

				<div class="space-y-1.5">
					<label class="field-label">Auto-open delay</label>
					<Select.Root type="single" bind:value={autoOpenDelayValue}>
						<Select.Trigger class="w-full justify-between">
							<span>{selectedAutoOpenDelayLabel}</span>
						</Select.Trigger>
						<Select.Content>
							{#each autoOpenDelayOptions as option}
								<Select.Item value={option.value} label={option.label}>{option.label}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				</div>

				<div class="flex items-center justify-between">
					<div>
						<p class="text-xs font-medium" style="color:var(--text-main)">Show unread badge</p>
						<p class="text-[11px] text-muted-foreground">
							Display a dot on the launcher when there's an unread message
						</p>
					</div>
					<Switch bind:checked={cfg.show_unread_badge} />
				</div>
			</div>
		</Accordion.Content>
	</Accordion.Item>

	<!-- 4. Language & Copy -->
	<Accordion.Item value="language">
		<Accordion.Trigger class="px-1 hover:no-underline">
			<span class="flex items-center gap-2 text-sm font-medium" style="color:var(--text-main)">
				Language &amp; copy
				<span class="text-[11px] font-normal text-muted-foreground"
					>Locale, UI messages</span
				>
			</span>
		</Accordion.Trigger>
		<Accordion.Content class="px-1">
			<div class="space-y-4 pb-2">
				<div class="space-y-1.5">
					<p class="field-label">Fallback language</p>
					<p class="text-[11px] text-muted-foreground">
						The widget reads the installed page's <code class="font-mono">html lang</code> attribute when available. This language is used when the page does not define one.
					</p>
					<Select.Root type="single" value={cfg.locale} onValueChange={applyLocale}>
						<Select.Trigger class="w-full justify-between">
							<span>{localeOptions.find((o) => o.value === cfg.locale)?.label ?? cfg.locale}</span>
						</Select.Trigger>
						<Select.Content>
							{#each localeOptions as option}
								<Select.Item value={option.value} label={option.label}>
									<span class="flex items-center gap-2">
										{option.label}
										{#if option.value === cfg.locale}
											<span class="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">Default</span>
										{/if}
									</span>
								</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
					<p class="text-[11px] text-muted-foreground">
						Supported languages: {localeOptions.map((o) => o.label).join(', ')}.
					</p>
				</div>

				<div class="space-y-2">
					<div>
						<label class="field-label">Widget interface copy</label>
						<p class="text-[11px] text-muted-foreground">
							Customize each supported language. The installed widget chooses the tab matching the page language, then falls back to the language above.
						</p>
					</div>
					<Tabs.Root bind:value={copyLocale} class="gap-3">
						<Tabs.List variant="line" class="max-w-full flex-wrap justify-start gap-1">
							{#each localeOptions as option}
								<Tabs.Trigger value={option.value} class="flex-none px-2 py-1">
									{option.value}
								</Tabs.Trigger>
							{/each}
						</Tabs.List>
						{#each localeOptions as option}
							<Tabs.Content value={option.value} class="space-y-3">
								<div class="flex items-center justify-between gap-3 rounded border bg-[var(--canvas)] px-3 py-2" style="border-color:var(--ds-border)">
									<div>
										<p class="text-xs font-medium" style="color:var(--text-main)">{option.label}</p>
										<p class="text-[11px] text-muted-foreground">
											Used for pages with <code class="font-mono">lang="{option.value}"</code>{#if option.value === cfg.locale} and as fallback{/if}.
										</p>
									</div>
									<Button type="button" variant="ghost" size="xs" onclick={() => resetLocaleCopy(option.value)}>
										Reset
									</Button>
								</div>
								<div class="grid gap-2 sm:grid-cols-2">
									{#each uiMessageFields as item}
										<div class="space-y-1">
											<label class="text-[10px] font-semibold tracking-widest text-muted-foreground uppercase">
												{item.label}
											</label>
											<Input
												value={localeCopy(option.value)[item.key]}
												class="text-xs"
												placeholder={defaultMessagesForLocale(option.value)[item.key]}
												oninput={(event) =>
													updateLocaleCopy(
														option.value,
														item.key,
														(event.currentTarget as HTMLInputElement).value
													)}
											/>
										</div>
									{/each}
								</div>
							</Tabs.Content>
						{/each}
					</Tabs.Root>
				</div>
			</div>
		</Accordion.Content>
	</Accordion.Item>

	<!-- 5. Conversation Starters -->
	<Accordion.Item value="starters">
		<Accordion.Trigger class="px-1 hover:no-underline">
			<span class="flex items-center gap-2 text-sm font-medium" style="color:var(--text-main)">
				Conversation starters
				<span class="text-[11px] font-normal text-muted-foreground"
					>Opening message, quick replies</span
				>
			</span>
		</Accordion.Trigger>
		<Accordion.Content class="px-1">
			<div class="space-y-4 pb-2">
				<div class="space-y-1.5">
					<label class="field-label">Opening message</label>
					<p class="text-[11px] text-muted-foreground">
						Sent automatically when the widget is first opened
					</p>
					<Textarea
						bind:value={cfg.opening_message}
						rows={2}
						placeholder="Hi! How can I help you today?"
					/>
				</div>

				<div class="space-y-1.5">
					<label class="field-label">
						Quick reply chips
						<span class="font-normal tracking-normal lowercase">({cfg.quick_replies.length}/4)</span
						>
					</label>
					<p class="text-[11px] text-muted-foreground">
						Tappable suggestion buttons shown below the opening message
					</p>

					{#if cfg.quick_replies.length > 0}
						<div class="flex flex-wrap gap-1.5 pb-1">
							{#each cfg.quick_replies as reply, i}
								<span
									class="flex items-center gap-1 rounded-full border px-3 py-1 text-xs"
									style="border-color:var(--ds-border);color:var(--text-main)"
								>
									{reply}
									<button
										onclick={() => removeReply(i)}
										class="ml-0.5 text-muted-foreground hover:text-foreground"
									>
										<X class="size-3" />
									</button>
								</span>
							{/each}
						</div>
					{/if}

					{#if cfg.quick_replies.length < 4}
						<div class="flex gap-2">
							<Input
								bind:value={newReply}
								placeholder="e.g. What are your hours?"
								class="text-xs"
								onkeydown={handleReplyKeydown}
							/>
							<Button variant="outline" size="sm" onclick={addReply} disabled={!newReply.trim()}>
								<Plus class="mr-1 size-3.5" /> Add
							</Button>
						</div>
					{/if}
				</div>
			</div>
		</Accordion.Content>
	</Accordion.Item>

	<!-- 6. Behavior -->
	<Accordion.Item value="behavior">
		<Accordion.Trigger class="px-1 hover:no-underline">
			<span class="flex items-center gap-2 text-sm font-medium" style="color:var(--text-main)">
				Behavior
				<span class="text-[11px] font-normal text-muted-foreground">Indicators, mobile</span>
			</span>
		</Accordion.Trigger>
		<Accordion.Content class="px-1">
			<div class="divide-y pb-2" style="divide-color:var(--ds-border)">
				{#each [{ key: 'typing_indicator' as const, label: 'Typing indicator', desc: 'Show animated dots while the bot is composing a reply' }, { key: 'sound_enabled' as const, label: 'Sound notifications', desc: 'Play a sound when a new message arrives' }, { key: 'mobile_fullscreen' as const, label: 'Mobile fullscreen', desc: 'Expand the widget to fill the screen on mobile devices' }] as item}
					<div class="flex items-center justify-between py-3 first:pt-0 last:pb-0">
						<div>
							<p class="text-xs font-medium" style="color:var(--text-main)">{item.label}</p>
							<p class="text-[11px] text-muted-foreground">{item.desc}</p>
						</div>
						<Switch bind:checked={cfg[item.key]} />
					</div>
				{/each}
			</div>
		</Accordion.Content>
	</Accordion.Item>

	<!-- 7. Access Control -->
	<Accordion.Item value="access">
		<Accordion.Trigger class="px-1 hover:no-underline">
			<span class="flex items-center gap-2 text-sm font-medium" style="color:var(--text-main)">
				Access control
				<span class="text-[11px] font-normal text-muted-foreground">Domain allowlist</span>
			</span>
		</Accordion.Trigger>
		<Accordion.Content class="px-1">
			<div class="space-y-2 pb-2">
				<label class="field-label">Allowed domains</label>
				<Textarea
					bind:value={domains}
					rows={3}
					placeholder="example.com&#10;app.example.com&#10;staging.example.com"
					class="font-mono text-xs"
				/>
				<p class="text-[11px] text-muted-foreground">
					One domain per line. The widget will refuse to load on any origin not listed here. Leave
					empty to allow all origins (not recommended for production).
				</p>
			</div>
		</Accordion.Content>
	</Accordion.Item>
</Accordion.Root>

<section class="mt-4 border-t px-1 pt-5" style="border-color:var(--ds-border)">
	<div class="mb-4">
		<div class="flex items-center gap-2 text-sm font-medium" style="color:var(--text-main)">
			Deploy &amp; Installation
			<span class="text-[11px] font-normal text-muted-foreground">Embed instructions</span>
		</div>
		<p class="mt-1 text-[11px] text-muted-foreground">
			Copy the snippet after saving, add it once per page, and verify the widget from the same
			domains you allow below.
		</p>
	</div>

	<div class="space-y-5 pb-2">
		<!-- Embed snippet -->
		<div class="space-y-1.5">
			<label class="field-label">Embed snippet</label>
			<div class="flex items-start gap-2">
				<pre
					class="flex-1 overflow-x-auto rounded border bg-canvas p-3 font-mono text-[11px] leading-relaxed"
					style="border-color:var(--ds-border)">{snippet}</pre>
				<Button variant="outline" size="icon-sm" onclick={copySnippet}>
					<Copy />
				</Button>
			</div>
		</div>

			<!-- Framework examples accordion -->
		<div class="space-y-1.5">
			<Accordion.Root type="multiple" class="w-full">
				<Accordion.Item value="frameworks" class="border-none">
					<Accordion.Trigger class="px-0 py-2 hover:no-underline">
						<p class="field-label">Framework examples</p>
					</Accordion.Trigger>
					<Accordion.Content>
							<div class="grid gap-1.5 pb-1">
							{#each frameworks as fw}
								{@const FwIcon = getLucideIcon(fw.icon)}
								<button
									onclick={() => {
										activeFrameworkId = fw.id;
										frameworkDialogOpen = true;
									}}
										class="flex w-full items-center gap-3 rounded-lg border px-3 py-2 text-left transition-colors hover:bg-accent"
									style="border-color:var(--ds-border)"
								>
									<div
										class="flex size-8 shrink-0 items-center justify-center rounded-md"
										style="background:{fw.color}18"
									>
										<FwIcon class="size-4" style="color:{fw.color}" />
									</div>
										<div class="flex min-w-0 flex-1 flex-col justify-center gap-0">
											<p class="m-0 text-xs font-medium leading-4" style="color:var(--text-main)">{fw.name}</p>
											<p class="m-0 text-[11px] leading-4 text-muted-foreground">{fw.description}</p>
										</div>
									<ChevronRight class="size-3.5 shrink-0 text-muted-foreground" />
								</button>
							{/each}
						</div>
					</Accordion.Content>
				</Accordion.Item>
			</Accordion.Root>
		</div>

		<details>
			<summary
				class="cursor-pointer text-[11px] font-medium text-muted-foreground select-none hover:text-foreground"
				>View config as JSON</summary
			>
			<pre
				class="mt-2 overflow-x-auto rounded border bg-canvas p-3 font-mono text-[10px] leading-relaxed"
				style="border-color:var(--ds-border)">{JSON.stringify(cfg, null, 2)}</pre>
		</details>
	</div>
</section>

<!-- Framework code dialog -->
{#if activeFramework}
	{@const FwIcon = getLucideIcon(activeFramework.icon)}
	<Dialog.Root bind:open={frameworkDialogOpen}>
		<Dialog.Content
			class="max-h-[calc(100vh-2rem)] w-[calc(100vw-2rem)] max-w-none gap-0 overflow-hidden p-0 sm:w-[min(1120px,calc(100vw-4rem))]"
		>
			<Dialog.Header class="border-b px-5 py-4 pr-12" style="border-color:var(--ds-border)">
				<Dialog.Title class="flex min-w-0 items-center gap-3 text-base">
					<div
						class="flex size-9 shrink-0 items-center justify-center rounded-md"
						style="background:{activeFramework.color}18"
					>
						<FwIcon class="size-5" style="color:{activeFramework.color}" />
					</div>
					<span class="truncate">{activeFramework.name}</span>
				</Dialog.Title>
				<Dialog.Description class="mt-1 text-sm leading-6">
					{activeFramework.description}. Add this once to your app's root layout or entry page.
				</Dialog.Description>
			</Dialog.Header>

			<div class="min-h-0 px-5 py-4">
				<div
					class="overflow-hidden rounded-lg border bg-canvas"
					style="border-color:var(--ds-border)"
				>
					<div
						class="flex items-center justify-between gap-3 border-b px-4 py-2.5"
						style="border-color:var(--ds-border)"
					>
						<div class="min-w-0">
							<p class="text-xs font-semibold" style="color:var(--text-main)">Install snippet</p>
							<p class="text-[11px] text-muted-foreground">
								Long lines wrap inside the panel so the dialog never overflows.
							</p>
						</div>
						<Button
							variant="outline"
							size="sm"
							class="shrink-0"
							onclick={() => {
								navigator.clipboard.writeText(activeFramework!.code);
								toast.success('Code copied.');
							}}
						>
							<Copy class="mr-1.5 size-3.5" /> Copy
						</Button>
					</div>
					<div class="max-h-[min(520px,calc(100vh-17rem))] overflow-y-auto">
						<pre class="whitespace-pre-wrap break-words p-5 font-mono text-sm leading-6 tabular-nums"><code
								>{activeFramework.code}</code
							></pre>
					</div>
				</div>
			</div>

			<Dialog.Footer class="border-t px-5 py-4" style="border-color:var(--ds-border)">
				<Dialog.Close>
					{#snippet child({ props })}
						<Button variant="outline" {...props}>Close</Button>
					{/snippet}
				</Dialog.Close>
				<Button
					onclick={() => {
						navigator.clipboard.writeText(activeFramework!.code);
						toast.success('Code copied.');
					}}
				>
					<Copy class="mr-1.5 size-3.5" /> Copy code
				</Button>
			</Dialog.Footer>
		</Dialog.Content>
	</Dialog.Root>
{/if}

<style>
	:global(.field-label) {
		display: block;
		font-size: 11px;
		font-weight: 600;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--muted-foreground);
	}
</style>
