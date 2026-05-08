export interface AgentModelOption {
	value: string;
	label: string;
}

export interface AgentTemplateOption {
	name: string;
	description: string;
	core_prompt: string;
}

export interface AgentUiSettings {
	default_model: string;
	models: AgentModelOption[];
	templates: AgentTemplateOption[];
	test_panel_enabled: boolean;
}

const DEFAULT_AGENT_UI: AgentUiSettings = {
	default_model: 'gpt-4o-mini',
	models: [
		{ value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
		{ value: 'gpt-4o', label: 'GPT-4o' },
		{ value: 'gpt-4.1-mini', label: 'GPT-4.1 Mini' }
	],
	templates: [
		{
			name: 'Support Agent',
			description: 'Answers customer questions using tenant knowledge and clear escalation rules.',
			core_prompt:
				'You are a support agent. Answer clearly, use available knowledge, and escalate when confidence is low.'
		},
		{
			name: 'Sales Assistant',
			description: 'Qualifies leads, explains offers, and prepares next-step summaries.',
			core_prompt:
				'You are a sales assistant. Ask concise qualifying questions and recommend the next best action.'
		},
		{
			name: 'Knowledge Analyst',
			description:
				'Researches tenant documents and produces structured answers with citations when possible.',
			core_prompt:
				'You are a knowledge analyst. Synthesize information from approved sources and explain uncertainty.'
		}
	],
	test_panel_enabled: true
};

export function getAgentUiSettings(publicSettings?: { public_settings?: Record<string, unknown> }): AgentUiSettings {
	const raw = publicSettings?.public_settings?.agent_ui;
	if (!raw || typeof raw !== 'object') return DEFAULT_AGENT_UI;
	const value = raw as Partial<AgentUiSettings>;
	return {
		default_model: typeof value.default_model === 'string' ? value.default_model : DEFAULT_AGENT_UI.default_model,
		models: Array.isArray(value.models) && value.models.length > 0 ? value.models : DEFAULT_AGENT_UI.models,
		templates:
			Array.isArray(value.templates) && value.templates.length > 0
				? value.templates
				: DEFAULT_AGENT_UI.templates,
		test_panel_enabled:
			typeof value.test_panel_enabled === 'boolean'
				? value.test_panel_enabled
				: DEFAULT_AGENT_UI.test_panel_enabled
	};
}

export function defaultAgentUiPublicSettings(): Record<string, unknown> {
	return { agent_ui: DEFAULT_AGENT_UI };
}
