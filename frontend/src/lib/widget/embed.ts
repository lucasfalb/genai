import WidgetApp from './widget-app.svelte';
import { mount } from 'svelte';

const script = document.currentScript as HTMLScriptElement | null;
const instanceId = script?.dataset.instance;
const apiBase = import.meta.env.PUBLIC_API_BASE_URL;

if (!instanceId) {
	console.warn('[genai-widget] Missing required data-instance attribute.');
} else if (!apiBase) {
	console.warn('[genai-widget] Missing PUBLIC_API_BASE_URL environment value.');
} else {
	const host = document.createElement('genai-chat-widget');
	document.body.appendChild(host);
	const shadow = host.attachShadow({ mode: 'open' });
	const mountEl = document.createElement('div');
	shadow.appendChild(mountEl);

	mount(WidgetApp, {
		target: mountEl,
		props: {
			instanceId,
			apiBase
		}
	});
}
