<script lang="ts">
	import * as LucideIcons from '@lucide/svelte/icons';
	import Accessibility from '@lucide/svelte/icons/accessibility';
	import Bot from '@lucide/svelte/icons/bot';
	import Mic from '@lucide/svelte/icons/mic';
	import MessageCircle from '@lucide/svelte/icons/message-circle';
	import Send from '@lucide/svelte/icons/send';
	import Square from '@lucide/svelte/icons/square';
	import X from '@lucide/svelte/icons/x';
	import type { WebWidgetConfig } from '$lib/api/types';
	import { renderFormattedMessage } from '$lib/utils/rich-message';

	let { config }: { config: WebWidgetConfig } = $props();

	const radiusMap: Record<WebWidgetConfig['border_radius'], string> = {
		sharp: '0px',
		rounded: '18px',
		full: '26px'
	};

	const iconRegistry = LucideIcons as unknown as Record<string, typeof MessageCircle>;
	const radius = $derived(radiusMap[config.border_radius] ?? '18px');
	const isLeft = $derived(config.position === 'bottom-left');
	const LauncherIcon = $derived(getLucideIcon(config.launcher_icon || 'message-circle'));
	const AvatarIcon = $derived(getLucideIcon(config.avatar_icon || 'bot') ?? Bot);
	const openingHtml = $derived(
		renderFormattedMessage(
			config.opening_message || `Hi, I'm ${config.bot_name || 'Assistant'}. How can I help?`
		)
	);

	function kebabToPascal(value: string) {
		return value
			.split('-')
			.map((part) => part.charAt(0).toUpperCase() + part.slice(1))
			.join('');
	}

	function getLucideIcon(value: string | null | undefined) {
		const name = kebabToPascal(value || '');
		return iconRegistry[name] ?? MessageCircle;
	}

	function initials(name: string) {
		return (
			name
				.split(' ')
				.map((w) => w[0])
				.join('')
				.slice(0, 2)
				.toUpperCase() || 'AI'
		);
	}
</script>

<div class="flex h-full flex-col" style="background:var(--surface)">
	<div
		class="flex h-10 shrink-0 items-center justify-between border-b px-4"
		style="border-color:var(--ds-border)"
	>
		<span class="text-[11px] font-semibold tracking-widest text-muted-foreground uppercase"
			>Widget Preview</span
		>
		<span
			class="rounded-full border px-2 py-0.5 text-[10px] text-muted-foreground"
			style="border-color:var(--ds-border)">Live</span
		>
	</div>

	<div class="relative flex-1 overflow-hidden bg-[#eef2f7]">
		<div class="absolute inset-0 p-6 opacity-35">
			<div class="mb-4 h-4 w-2/3 rounded-full bg-slate-400"></div>
			<div class="mb-2 h-2.5 w-full rounded-full bg-slate-300"></div>
			<div class="mb-2 h-2.5 w-5/6 rounded-full bg-slate-300"></div>
			<div class="mt-7 grid grid-cols-2 gap-3">
				<div class="h-24 rounded-lg bg-white/80 shadow-sm"></div>
				<div class="h-24 rounded-lg bg-white/80 shadow-sm"></div>
			</div>
			<div class="mt-5 h-2.5 w-3/4 rounded-full bg-slate-300"></div>
			<div class="mt-2 h-2.5 w-full rounded-full bg-slate-300"></div>
		</div>

		<div
			class="absolute bottom-5 flex flex-col gap-3"
			style={isLeft ? 'left:18px;align-items:flex-start' : 'right:18px;align-items:flex-end'}
		>
			<div
				class="flex w-[292px] flex-col overflow-hidden border shadow-2xl"
				style="height:420px;border-radius:{radius};background:{config.bg_color};border-color:rgba(15,23,42,0.12);box-shadow:0 28px 70px rgba(15,23,42,0.28)"
			>
				<div
					class="relative shrink-0 px-4 py-3.5 text-white"
					style="background:radial-gradient(circle at 0% 0%, rgba(255,255,255,0.22), transparent 32%), linear-gradient(135deg, color-mix(in srgb, {config.primary_color} 94%, #ffffff 6%), color-mix(in srgb, {config.primary_color} 82%, #000000 18%))"
				>
					<div class="flex items-center gap-3">
						<div
							class="flex size-10 shrink-0 items-center justify-center overflow-hidden rounded-2xl border border-white/20 bg-white/20 text-xs font-bold"
						>
							{#if config.avatar_mode === 'image' && config.avatar_image_url}
								<img src={config.avatar_image_url} alt="" class="size-full object-cover" />
							{:else if config.avatar_mode === 'icon'}
								<AvatarIcon class="size-5" />
							{:else}
								{initials(config.bot_name)}
							{/if}
						</div>
						<div class="min-w-0 flex-1">
							<p class="truncate text-[15px] leading-5 font-bold">{config.title}</p>
							{#if config.subtitle}
								<p class="truncate text-xs leading-4 text-white/75">{config.subtitle}</p>
							{/if}
						</div>
						<div
							class="flex size-8 items-center justify-center rounded-full bg-white/15 text-white/90"
						>
							<Accessibility class="size-4" />
						</div>
						<div
							class="flex size-8 items-center justify-center rounded-full bg-white/15 text-white/90"
						>
							<X class="size-4" />
						</div>
					</div>
				</div>

				<div class="flex flex-1 flex-col overflow-hidden px-3 py-4">
					<div class="flex items-end gap-2">
						<div
							class="flex size-7 shrink-0 items-center justify-center rounded-[10px] text-[10px] font-bold"
							style="background:color-mix(in srgb, {config.primary_color} 12%, #ffffff 88%);color:{config.primary_color}"
						>
							{config.avatar_mode === 'icon' ? '' : initials(config.bot_name)}
							{#if config.avatar_mode === 'icon'}<AvatarIcon class="size-4" />{/if}
						</div>
						<div
							class="max-w-[82%] rounded-[17px] rounded-bl-md border border-slate-200 bg-white px-3 py-2 text-xs leading-5 text-slate-900 shadow-sm"
						>
							<div class="preview-rich-message">{@html openingHtml}</div>
						</div>
					</div>

					{#if config.quick_replies.length > 0}
						<div class="mt-2 ml-9 flex flex-wrap gap-1.5">
							{#each config.quick_replies.slice(0, 3) as reply}
								<span
									class="rounded-full border px-2.5 py-1 text-[11px]"
									style="border-color:color-mix(in srgb, {config.primary_color} 35%, transparent);background:color-mix(in srgb, {config.primary_color} 7%, #ffffff 93%);color:{config.primary_color}"
									>{reply}</span
								>
							{/each}
						</div>
					{/if}

					<div class="mt-3 flex justify-end">
						<div
							class="max-w-[82%] rounded-[17px] rounded-br-md px-3 py-2 text-xs leading-5 text-white shadow-sm"
							style="background:{config.primary_color}"
						>
							I'd like to know more.
						</div>
					</div>

					<div class="mt-3 flex items-end gap-2">
						<div
							class="flex size-7 shrink-0 items-center justify-center rounded-[10px] text-[10px] font-bold"
							style="background:color-mix(in srgb, {config.primary_color} 12%, #ffffff 88%);color:{config.primary_color}"
						>
							{initials(config.bot_name)}
						</div>
						<div
							class="inline-flex rounded-[17px] rounded-bl-md border border-slate-200 bg-white px-3 py-2.5 shadow-sm"
						>
							<span class="mx-0.5 size-1.5 animate-bounce rounded-full bg-slate-400"></span>
							<span
								class="mx-0.5 size-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:150ms]"
							></span>
							<span
								class="mx-0.5 size-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:300ms]"
							></span>
						</div>
					</div>
				</div>

				<div class="shrink-0 border-t bg-white/80 p-3" style="border-color:rgba(15,23,42,0.08)">
					<div
						class="flex items-end gap-2 rounded-[22px] border border-slate-200 bg-white py-1.5 pr-1.5 pl-3 shadow-sm"
					>
						<div class="flex-1 py-1.5 text-xs text-slate-400">Type a message...</div>
						<div
							class="flex size-8 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-slate-500"
						>
							<Mic class="size-4" />
						</div>
						<div
							class="flex size-8 items-center justify-center rounded-full text-white"
							style="background:{config.primary_color}"
						>
							<Send class="size-4" />
						</div>
					</div>
				</div>
			</div>

			<div class="relative">
				<button
					class="grid size-16 place-items-center rounded-full text-white shadow-2xl transition-transform hover:scale-105"
					style="background:radial-gradient(circle at 32% 22%, rgba(255,255,255,0.28), transparent 36%), linear-gradient(145deg, color-mix(in srgb, {config.primary_color} 90%, #ffffff 10%), color-mix(in srgb, {config.primary_color} 86%, #000000 14%))"
				>
					{#if config.launcher_mode === 'image' && config.launcher_image_url}
						<img src={config.launcher_image_url} alt="" class="size-9 rounded-full object-cover" />
					{:else}
						<LauncherIcon class="size-7" />
					{/if}
				</button>
				{#if config.show_unread_badge}
					<span
						class="absolute top-1 right-1 size-4 rounded-full border-2 border-white bg-red-500 shadow"
					></span>
				{/if}
			</div>
		</div>
	</div>

	<div
		class="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-1 border-t px-4 py-2.5"
		style="border-color:var(--ds-border)"
	>
		<span class="text-[10px] text-muted-foreground"
			><span class="font-medium" style="color:var(--text-main)">Font:</span>
			{config.font_family}</span
		>
		<span class="text-[10px] text-muted-foreground"
			><span class="font-medium" style="color:var(--text-main)">Radius:</span>
			{config.border_radius}</span
		>
		<span class="text-[10px] text-muted-foreground"
			><span class="font-medium" style="color:var(--text-main)">Position:</span>
			{config.position}</span
		>
		<span class="flex items-center gap-1 text-[10px] text-muted-foreground"
			><span class="inline-block size-2.5 rounded-sm" style="background:{config.primary_color}"
			></span>{config.primary_color}</span
		>
	</div>
</div>

<style>
	.preview-rich-message {
		white-space: normal;
	}
	.preview-rich-message :global(p) {
		margin: 0 0 0.65em;
	}
	.preview-rich-message :global(p:last-child),
	.preview-rich-message :global(ul:last-child),
	.preview-rich-message :global(h3:last-child),
	.preview-rich-message :global(h4:last-child) {
		margin-bottom: 0;
	}
	.preview-rich-message :global(ul) {
		margin: 0.3em 0 0.7em;
		padding-left: 1.15em;
	}
	.preview-rich-message :global(li) {
		margin: 0.18em 0;
	}
	.preview-rich-message :global(strong) {
		font-weight: 750;
	}
	.preview-rich-message :global(code) {
		border-radius: 5px;
		background: rgba(15, 23, 42, 0.08);
		padding: 0.05em 0.28em;
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 0.9em;
	}
	.preview-rich-message :global(a) {
		color: inherit;
		font-weight: 700;
		text-decoration: underline;
		text-underline-offset: 2px;
	}
	.preview-rich-message :global(h3),
	.preview-rich-message :global(h4) {
		margin: 0.1em 0 0.4em;
		font-size: 1em;
		line-height: 1.3;
		font-weight: 800;
	}
</style>
