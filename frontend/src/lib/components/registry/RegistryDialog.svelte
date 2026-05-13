<script lang="ts">
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import * as Command from '$lib/components/ui/command/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import JsonEditor from './JsonEditor.svelte';
	import KeyValueJsonEditor from './KeyValueJsonEditor.svelte';
	import VariablesJsonEditor from './VariablesJsonEditor.svelte';
	import type { ToolDefinitionResponse, SkillDefinitionResponse } from '$lib/api/types';
	import Code from '@lucide/svelte/icons/code';
	import TableProperties from '@lucide/svelte/icons/table-properties';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Check from '@lucide/svelte/icons/check';
	import FileJson from '@lucide/svelte/icons/file-json';
	import { cn } from '$lib/utils.js';

	const CATEGORIES = [
		'analytics',
		'communication',
		'crm',
		'data',
		'documentation',
		'entertainment',
		'finance',
		'geolocation',
		'health',
		'news',
		'productivity',
		'rag',
		'reference',
		'search',
		'security',
		'social',
		'testing',
		'utility',
		'weather',
		'web'
	] as const;

	const KNOWN_EXECUTORS = ['web_fetch'] as const;

	type EntityType = 'tool' | 'skill';
	type DialogMode = 'create' | 'edit';
	type JsonField =
		| 'advanced'
		| 'schema'
		| 'headers_template'
		| 'body_template'
		| 'variables_schema'
		| 'tool_schema'
		| 'input_schema'
		| 'output_schema'
		| 'credential_schema';

	let {
		open = $bindable(false),
		type: entityType,
		mode,
		tool,
		skill,
		busy,
		onSave,
		onDelete
	}: {
		open: boolean;
		type: EntityType;
		mode: DialogMode;
		tool?: ToolDefinitionResponse | null;
		skill?: SkillDefinitionResponse | null;
		busy: boolean;
		onSave: (payload: Record<string, unknown>) => Promise<void>;
		onDelete: () => Promise<void>;
	} = $props();

	let advanced = $state(false);
	let deleteConfirm = $state(false);

	let editingItem = $derived(tool ?? skill);

	// Common form fields
	let formSlug = $state('');
	let formName = $state('');
	let formDescription = $state('');
	let formCategory = $state('');
	let formPromptBlock = $state('');
	let formExecutor = $state('');
	let formIsBuiltin = $state(false);
	let formIsActive = $state(true);
	let formRequiresCredential = $state(false);
	let formSchema = $state('{}');
	let formToolSchema = $state('{}');
	let formInputSchema = $state('{}');
	let formOutputSchema = $state('{}');
	let formCredentialSchema = $state('{}');

	// HTTP config fields (tools with web_fetch executor)
	let formMethod = $state('GET');
	let formEndpoint = $state('');
	let formHeadersTemplate = $state('{}');
	let formBodyTemplate = $state('');
	let formVariablesSchema = $state('[]');

	let jsonRaw = $state('{}');
	let jsonError = $state('');
	let jsonFieldErrors = $state<Record<string, string>>({});
	let initializedKey = $state('');

	const title = $derived(
		mode === 'create'
			? `New ${entityType === 'tool' ? 'Tool' : 'Skill'}`
			: `Edit ${editingItem?.slug ?? ''}`
	);

	const isWebFetch = $derived(formExecutor === 'web_fetch');

	$effect(() => {
		const item = editingItem;
		const itemSlug = item && 'slug' in item ? item.slug : 'new';
		const nextInitializedKey = open ? `${entityType}:${mode}:${itemSlug}` : '';
		if (!open) {
			initializedKey = '';
			return;
		}
		if (initializedKey === nextInitializedKey) return;
		initializedKey = nextInitializedKey;

		advanced = false;
		jsonError = '';
		jsonFieldErrors = {};
		deleteConfirm = false;

		let nextHeadersTemplate = '{}';
		let nextBodyTemplate = '';
		let nextVariablesSchema = '[]';

		if (item && mode === 'edit') {
			formSlug = 'slug' in item ? item.slug : '';
			formName = item.name;
			formDescription = item.description ?? '';
			formCategory = item.category ?? '';
			formPromptBlock = item.prompt_block ?? '';
			formExecutor = item.executor ?? '';
			formIsBuiltin = 'is_builtin' in item ? item.is_builtin : false;
			formIsActive = 'is_active' in item ? item.is_active : true;
			formRequiresCredential = 'requires_credential' in item ? item.requires_credential : false;
			formSchema = JSON.stringify('schema' in item ? (item.schema ?? {}) : {}, null, 2);
			formToolSchema = JSON.stringify(
				'tool_schema' in item ? (item.tool_schema ?? {}) : {},
				null,
				2
			);
			formInputSchema = JSON.stringify(
				'input_schema' in item ? (item.input_schema ?? {}) : {},
				null,
				2
			);
			formOutputSchema = JSON.stringify(
				'output_schema' in item ? (item.output_schema ?? {}) : {},
				null,
				2
			);
			formCredentialSchema = JSON.stringify(
				'credential_schema' in item ? (item.credential_schema ?? {}) : {},
				null,
				2
			);
			// HTTP fields
			if ('method' in item) formMethod = (item as any).method ?? 'GET';
			if ('endpoint' in item) formEndpoint = (item as any).endpoint ?? '';
			if ('headers_template' in item)
				nextHeadersTemplate = JSON.stringify((item as any).headers_template ?? {}, null, 2);
			if ('body_template' in item) nextBodyTemplate = (item as any).body_template ?? '';
			if ('variables_schema' in item)
				nextVariablesSchema = JSON.stringify((item as any).variables_schema ?? [], null, 2);
			formHeadersTemplate = nextHeadersTemplate;
			formBodyTemplate = nextBodyTemplate;
			formVariablesSchema = nextVariablesSchema;
			jsonRaw = JSON.stringify(initialPayloadFromItem(item), null, 2);
		} else {
			formSlug = '';
			formName = '';
			formDescription = '';
			formCategory = '';
			formPromptBlock = '';
			formExecutor = '';
			formIsBuiltin = false;
			formIsActive = true;
			formRequiresCredential = false;
			formSchema = '{}';
			formToolSchema = '{}';
			formInputSchema = '{}';
			formOutputSchema = '{}';
			formCredentialSchema = '{}';
			formMethod = 'GET';
			formEndpoint = '';
			formHeadersTemplate = nextHeadersTemplate;
			formBodyTemplate = nextBodyTemplate;
			formVariablesSchema = nextVariablesSchema;
			jsonRaw = '{}';
		}
	});

	function initialPayloadFromItem(
		item: ToolDefinitionResponse | SkillDefinitionResponse
	): Record<string, unknown> {
		if ('schema' in item) {
			return {
				id: item.id,
				slug: item.slug,
				name: item.name,
				description: item.description ?? '',
				category: item.category ?? '',
				prompt_block: item.prompt_block,
				schema: item.schema ?? {},
				executor: item.executor,
				is_builtin: item.is_builtin,
				method: item.method,
				endpoint: item.endpoint,
				headers_template: item.headers_template ?? {},
				body_template: item.body_template,
				variables_schema: item.variables_schema ?? []
			};
		}
		return {
			id: item.id,
			slug: item.slug,
			name: item.name,
			description: item.description ?? '',
			category: item.category ?? '',
			prompt_block: item.prompt_block,
			executor: item.executor,
			is_active: item.is_active,
			requires_credential: item.requires_credential,
			tool_schema: item.tool_schema ?? {},
			input_schema: item.input_schema ?? {},
			output_schema: item.output_schema ?? {},
			credential_schema: item.credential_schema ?? {}
		};
	}

	function buildPayload(): Record<string, unknown> {
		const base: Record<string, unknown> = {
			slug: formSlug.trim(),
			name: formName.trim(),
			description: formDescription.trim(),
			category: formCategory.trim(),
			prompt_block: formPromptBlock,
			executor: formExecutor.trim()
		};
		if (entityType === 'tool') {
			base.is_builtin = formIsBuiltin;
			try {
				base.schema = JSON.parse(formSchema || '{}');
			} catch {
				base.schema = {};
			}
			base.method = formMethod;
			base.endpoint = formEndpoint.trim() || null;
			try {
				base.headers_template = JSON.parse(formHeadersTemplate || '{}');
			} catch {
				base.headers_template = {};
			}
			base.body_template = formBodyTemplate.trim() || null;
			try {
				base.variables_schema = JSON.parse(formVariablesSchema || '[]');
			} catch {
				base.variables_schema = [];
			}
		} else {
			base.is_active = formIsActive;
			base.requires_credential = formRequiresCredential;
			try {
				base.tool_schema = JSON.parse(formToolSchema || '{}');
			} catch {
				base.tool_schema = {};
			}
			try {
				base.input_schema = JSON.parse(formInputSchema || '{}');
			} catch {
				base.input_schema = {};
			}
			try {
				base.output_schema = JSON.parse(formOutputSchema || '{}');
			} catch {
				base.output_schema = {};
			}
			try {
				base.credential_schema = JSON.parse(formCredentialSchema || '{}');
			} catch {
				base.credential_schema = {};
			}
		}
		return base;
	}

	function getJsonValue(field: JsonField): string {
		switch (field) {
			case 'advanced':
				return jsonRaw;
			case 'schema':
				return formSchema;
			case 'headers_template':
				return formHeadersTemplate;
			case 'body_template':
				return formBodyTemplate || '{}';
			case 'variables_schema':
				return formVariablesSchema;
			case 'tool_schema':
				return formToolSchema;
			case 'input_schema':
				return formInputSchema;
			case 'output_schema':
				return formOutputSchema;
			case 'credential_schema':
				return formCredentialSchema;
		}
	}

	function setJsonValue(field: JsonField, value: string) {
		switch (field) {
			case 'advanced':
				jsonRaw = value;
				break;
			case 'schema':
				formSchema = value;
				break;
			case 'headers_template':
				formHeadersTemplate = value;
				break;
			case 'body_template':
				formBodyTemplate = value;
				break;
			case 'variables_schema':
				formVariablesSchema = value;
				break;
			case 'tool_schema':
				formToolSchema = value;
				break;
			case 'input_schema':
				formInputSchema = value;
				break;
			case 'output_schema':
				formOutputSchema = value;
				break;
			case 'credential_schema':
				formCredentialSchema = value;
				break;
		}
		if (jsonFieldErrors[field]) {
			jsonFieldErrors = { ...jsonFieldErrors, [field]: '' };
			jsonError = '';
		}
	}

	function setJsonFieldError(field: JsonField, message: string) {
		jsonFieldErrors = { ...jsonFieldErrors, [field]: message };
		jsonError = message;
	}

	function clearJsonFieldError(field: JsonField) {
		if (!jsonFieldErrors[field]) return;
		jsonFieldErrors = { ...jsonFieldErrors, [field]: '' };
		jsonError = '';
	}

	function validateSimple(): boolean {
		if (!formSlug.trim() || !formName.trim()) {
			jsonError = 'Slug and name are required.';
			return false;
		}
		if (!formExecutor.trim()) {
			jsonError = 'Executor is required.';
			return false;
		}
		if (entityType === 'tool') {
			for (const [field, value, label] of [
				['schema', formSchema, 'Schema JSON'],
				['headers_template', formHeadersTemplate, 'Headers template JSON'],
				['variables_schema', formVariablesSchema, 'Variables schema JSON']
			] as const) {
				try {
					JSON.parse(value || (field === 'variables_schema' ? '[]' : '{}'));
				} catch {
					setJsonFieldError(field, `${label} is invalid.`);
					return false;
				}
			}
			if (formBodyTemplate.trim()) {
				try {
					JSON.parse(formBodyTemplate);
				} catch {
					setJsonFieldError('body_template', 'Body template JSON is invalid.');
					return false;
				}
			}
		} else {
			for (const [field, label] of [
				['tool_schema', 'Tool schema'],
				['input_schema', 'Input schema'],
				['output_schema', 'Output schema'],
				['credential_schema', 'Credential schema']
			] as const) {
				try {
					JSON.parse(getJsonValue(field) || '{}');
				} catch {
					setJsonFieldError(field, `${label} JSON is invalid.`);
					return false;
				}
			}
		}
		jsonError = '';
		jsonFieldErrors = {};
		return true;
	}

	function validateAdvanced(): boolean {
		try {
			const parsed = JSON.parse(jsonRaw);
			if (!parsed.slug || !parsed.name) {
				jsonError = 'slug and name are required in JSON.';
				return false;
			}
			jsonError = '';
			return true;
		} catch {
			setJsonFieldError('advanced', 'Invalid JSON.');
			return false;
		}
	}

	async function handleSave() {
		const payload = advanced
			? (() => {
					try {
						return JSON.parse(jsonRaw);
					} catch {
						return {};
					}
				})()
			: buildPayload();

		if (advanced ? !validateAdvanced() : !validateSimple()) return;
		await onSave(payload);
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="flex max-h-[90vh] max-w-3xl flex-col overflow-hidden rounded-xl p-0">
		<Dialog.Header class="shrink-0">
			<div class="flex items-start gap-3 border-b px-5 py-4">
				<div class="flex size-9 shrink-0 items-center justify-center rounded-md border bg-muted/40">
					{#if advanced}
						<FileJson class="size-4 text-muted-foreground" />
					{:else}
						<TableProperties class="size-4 text-muted-foreground" />
					{/if}
				</div>
				<div class="min-w-0 flex-1">
					<Dialog.Title class="truncate text-base font-semibold">{title}</Dialog.Title>
					<Dialog.Description class="text-xs text-muted-foreground">
						{mode === 'create'
							? 'Create a reusable registry entry. Slug cannot be changed later.'
							: 'Review and update this registry entry. Slug is immutable.'}
					</Dialog.Description>
				</div>
			</div>
		</Dialog.Header>

		<div class="min-h-0 flex-1 overflow-y-auto px-5 py-4">
			<div class="flex flex-col gap-4">
				<div class="flex items-center gap-1 rounded-md border bg-muted/20 p-1">
					<button
						class="flex h-8 flex-1 items-center justify-center gap-1.5 rounded-sm px-3 text-xs font-medium transition-colors {!advanced
							? 'bg-background text-foreground shadow-sm'
							: 'text-muted-foreground hover:text-foreground'}"
						onclick={() => (advanced = false)}
					>
						<TableProperties class="size-3.5" />
						Form
					</button>
					<button
						class="flex h-8 flex-1 items-center justify-center gap-1.5 rounded-sm px-3 text-xs font-medium transition-colors {advanced
							? 'bg-background text-foreground shadow-sm'
							: 'text-muted-foreground hover:text-foreground'}"
						onclick={() => {
							if (!advanced) jsonRaw = JSON.stringify(buildPayload(), null, 2);
							advanced = true;
						}}
					>
						<Code class="size-3.5" />
						JSON
					</button>
				</div>

				{#if advanced}
					<JsonEditor
						field="advanced"
						value={jsonRaw}
						label="Complete payload"
						description="Edit the full request body sent to the API."
						rows={22}
						placeholder={'{\n  "slug": "web_fetch",\n  "name": "Web Fetch"\n}'}
						required
						error={jsonFieldErrors.advanced}
						onValueChange={setJsonValue}
						onError={setJsonFieldError}
						onClear={clearJsonFieldError}
					/>
				{:else}
					<div class="flex flex-col gap-4 py-2">
						{#if entityType === 'tool' && mode === 'edit'}
							{@const t = tool as ToolDefinitionResponse | undefined}
							<div class="flex items-center gap-3 rounded-lg border bg-muted/50 px-3 py-2.5">
								<div class="flex size-8 items-center justify-center rounded-md bg-blue-500/10">
									<span class="text-sm font-bold text-blue-400"
										>{t?.slug?.charAt(0).toUpperCase() ?? 'N'}</span
									>
								</div>
								<div class="min-w-0 flex-1">
									<p class="truncate text-sm font-medium">{t?.name ?? 'New Tool'}</p>
									<p class="truncate text-xs text-muted-foreground">{t?.slug ?? '—'}</p>
								</div>
								{#if t?.is_builtin}
									<span
										class="rounded-md bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
										>builtin</span
									>
								{/if}
							</div>
						{/if}

						{#if mode === 'create'}
							<div class="flex flex-col gap-1.5">
								<label for="registry-slug" class="text-xs font-medium text-muted-foreground">
									Slug <span class="text-red-400">*</span>
								</label>
								<Input
									id="registry-slug"
									bind:value={formSlug}
									placeholder={entityType === 'tool' ? 'my-tool' : 'my-skill'}
									class="font-mono text-xs"
								/>
							</div>
						{/if}

						<div class="grid grid-cols-3 gap-3">
							<div class="col-span-2 flex flex-col gap-1.5">
								<label for="registry-name" class="text-xs font-medium text-muted-foreground">
									Name <span class="text-red-400">*</span>
								</label>
								<Input
									id="registry-name"
									bind:value={formName}
									placeholder={`My ${entityType === 'tool' ? 'Tool' : 'Skill'}`}
									class="text-xs"
								/>
							</div>
							<div class="flex flex-col gap-1.5">
								<span class="text-xs font-medium text-muted-foreground">Category</span>
								<Popover.Root>
									<Popover.Trigger
										class="flex h-9 w-full items-center justify-between rounded-lg border bg-background px-3 text-left text-xs {formCategory
											? ''
											: 'text-muted-foreground'}"
									>
										{formCategory || 'Select...'}
										<ChevronDown class="size-3.5 shrink-0 opacity-50" />
									</Popover.Trigger>
									<Popover.Content class="w-48 p-0" align="start">
										<Command.Root>
											<Command.Input placeholder="Search..." class="h-9 text-xs" />
											<Command.List>
												<Command.Empty>No match.</Command.Empty>
												<Command.Group>
													{#each CATEGORIES as cat}
														<Command.Item
															value={cat}
															onSelect={() => (formCategory = cat)}
															class="text-xs"
														>
															<Check
																class={cn(
																	'mr-2 size-3.5',
																	formCategory === cat ? 'opacity-100' : 'opacity-0'
																)}
															/>
															{cat}
														</Command.Item>
													{/each}
												</Command.Group>
											</Command.List>
										</Command.Root>
									</Popover.Content>
								</Popover.Root>
							</div>
						</div>

						<div class="flex flex-col gap-1.5">
							<label for="registry-description" class="text-xs font-medium text-muted-foreground"
								>Description</label
							>
							<Input
								id="registry-description"
								bind:value={formDescription}
								placeholder="Brief description of what this does"
								class="text-xs"
							/>
						</div>

						<!-- Executor combobox + toggles -->
						<div class="grid grid-cols-2 gap-3">
							<div class="flex flex-col gap-1.5">
								<span class="text-xs font-medium text-muted-foreground">
									Executor <span class="text-red-400">*</span>
								</span>
								<Popover.Root>
									<Popover.Trigger
										class="flex h-9 w-full items-center justify-between rounded-lg border bg-background px-3 text-left text-xs {formExecutor
											? ''
											: 'text-muted-foreground'}"
									>
										{formExecutor || 'Select executor...'}
										<ChevronDown class="size-3.5 shrink-0 opacity-50" />
									</Popover.Trigger>
									<Popover.Content class="w-56 p-0" align="start">
										<Command.Root>
											<Command.Input placeholder="Search or type custom..." class="h-9 text-xs" />
											<Command.List>
												<Command.Empty>
													<button
														class="w-full px-3 py-2 text-left text-xs text-muted-foreground hover:text-foreground"
														onclick={() => {
															const input = document.querySelector(
																'#custom-executor-input'
															) as HTMLInputElement;
															if (input) formExecutor = input.value;
														}}
													>
														Type custom executor...
													</button>
												</Command.Empty>
												<Command.Group heading="Built-in executors">
													{#each KNOWN_EXECUTORS as exec}
														<Command.Item
															value={exec}
															onSelect={() => (formExecutor = exec)}
															class="text-xs"
														>
															<Check
																class={cn(
																	'mr-2 size-3.5',
																	formExecutor === exec ? 'opacity-100' : 'opacity-0'
																)}
															/>
															<span class="font-mono">{exec}</span>
														</Command.Item>
													{/each}
												</Command.Group>
											</Command.List>
											<div class="border-t p-2">
												<input
													id="custom-executor-input"
													type="text"
													placeholder="Custom executor name..."
													class="w-full rounded-md border bg-background px-2.5 py-1.5 font-mono text-xs outline-none"
													oninput={(e) => (formExecutor = e.currentTarget.value)}
												/>
											</div>
										</Command.Root>
									</Popover.Content>
								</Popover.Root>
							</div>
							{#if entityType === 'skill'}
								<div class="flex flex-col gap-2">
									<div class="flex items-center justify-between rounded-lg border px-3 py-2">
										<div>
											<p class="text-xs font-medium">Active</p>
											<p class="text-[10px] text-muted-foreground">Skill is available for use</p>
										</div>
										<Switch bind:checked={formIsActive} />
									</div>
									<div class="flex items-center justify-between rounded-lg border px-3 py-2">
										<div>
											<p class="text-xs font-medium">Requires Credential</p>
											<p class="text-[10px] text-muted-foreground">Needs external auth</p>
										</div>
										<Switch bind:checked={formRequiresCredential} />
									</div>
								</div>
							{/if}
						</div>

						<!-- HTTP config section (tools only, web_fetch executor) -->
						{#if entityType === 'tool' && isWebFetch}
							<div class="rounded-lg border">
								<div class="border-b bg-muted/50 px-3 py-2">
									<p class="text-xs font-medium text-muted-foreground">
										HTTP Request Configuration
									</p>
								</div>
								<div class="grid grid-cols-[100px_1fr] gap-3 p-3">
									<div class="flex flex-col gap-1.5">
										<label
											for="registry-method"
											class="text-[10px] font-medium text-muted-foreground">Method</label
										>
										<Select.Root type="single" bind:value={formMethod}>
											<Select.Trigger
												id="registry-method"
												class="h-9 w-full bg-background font-mono text-xs"
											>
												{formMethod}
											</Select.Trigger>
											<Select.Content>
												{#each ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'] as method}
													<Select.Item value={method} label={method}>{method}</Select.Item>
												{/each}
											</Select.Content>
										</Select.Root>
									</div>
									<div class="flex flex-col gap-1.5">
										<label
											for="registry-endpoint"
											class="text-[10px] font-medium text-muted-foreground"
										>
											Endpoint <span class="text-muted-foreground/50">({'{var}'} placeholders)</span
											>
										</label>
										<Input
											id="registry-endpoint"
											bind:value={formEndpoint}
											placeholder={'https://api.example.com/v1/{resource}'}
											class="font-mono text-xs"
										/>
									</div>
									<div class="col-span-2 flex flex-col gap-1.5">
										<KeyValueJsonEditor
											field="headers_template"
											value={formHeadersTemplate}
											label="Headers template"
											description={'Request headers sent with the HTTP call. Placeholders such as {token} are replaced at runtime.'}
											keyPlaceholder="Authorization"
											valuePlaceholder={'Bearer {token}'}
											resetKey={initializedKey}
											error={jsonFieldErrors.headers_template}
											onValueChange={setJsonValue}
											onError={setJsonFieldError}
											onClear={clearJsonFieldError}
										/>
									</div>
									<div class="col-span-2 flex flex-col gap-1.5">
										<KeyValueJsonEditor
											field="body_template"
											value={formBodyTemplate || '{}'}
											label="Body template"
											description="JSON body sent for POST, PUT, or PATCH. Values can use placeholders."
											keyPlaceholder=""
											valuePlaceholder={''}
											resetKey={initializedKey}
											error={jsonFieldErrors.body_template}
											onValueChange={setJsonValue}
											onError={setJsonFieldError}
											onClear={clearJsonFieldError}
										/>
									</div>
									<div class="col-span-2 flex flex-col gap-1.5">
										<VariablesJsonEditor
											value={formVariablesSchema}
											resetKey={initializedKey}
											error={jsonFieldErrors.variables_schema}
											onValueChange={setJsonValue}
											onError={setJsonFieldError}
											onClear={clearJsonFieldError}
										/>
										<p class="text-[10px] text-muted-foreground">
											Each variable: name, label, type (string/object), secret, required,
											description, default. Users configure these values when activating the tool on
											an instance.
										</p>
									</div>
								</div>
							</div>
						{/if}

						<!-- Prompt Block -->
						<div class="flex flex-col gap-1.5">
							<label for="registry-prompt-block" class="text-xs font-medium text-muted-foreground"
								>Prompt Block</label
							>
							<Textarea
								id="registry-prompt-block"
								bind:value={formPromptBlock}
								rows={3}
								class="font-mono text-xs"
								placeholder="Instructions the LLM receives about when to use this..."
							/>
						</div>

						<!-- Schema section -->
						<div class="rounded-lg border">
							<div class="border-b bg-muted/50 px-3 py-2">
								<p class="text-xs font-medium text-muted-foreground">LLM Function Schema</p>
							</div>
							<div class="p-3">
								{#if entityType === 'tool'}
									<div class="flex flex-col gap-1.5">
										<JsonEditor
											field="schema"
											value={formSchema}
											label="Function schema"
											description="The function signature the LLM sees: name, description, parameters and required fields."
											rows={9}
											placeholder={'{\n  "name": "my_func",\n  "description": "Describe what this tool does.",\n  "parameters": {\n    "type": "object",\n    "properties": {}\n  }\n}'}
											required
											error={jsonFieldErrors.schema}
											onValueChange={setJsonValue}
											onError={setJsonFieldError}
											onClear={clearJsonFieldError}
										/>
										<p class="text-[10px] text-muted-foreground">
											Defines the function signature the LLM sees: name, description, parameters
											with properties and required.
										</p>
									</div>
								{:else}
									<div class="grid grid-cols-2 gap-3">
										<JsonEditor
											field="tool_schema"
											value={formToolSchema}
											label="Tool schema"
											description="Function schema exposed by this skill."
											rows={7}
											placeholder={'{\n  "name": "skill_name",\n  "parameters": {\n    "type": "object"\n  }\n}'}
											error={jsonFieldErrors.tool_schema}
											onValueChange={setJsonValue}
											onError={setJsonFieldError}
											onClear={clearJsonFieldError}
										/>
										<JsonEditor
											field="input_schema"
											value={formInputSchema}
											label="Input schema"
											description="Expected input shape for validation and documentation."
											rows={7}
											placeholder={'{\n  "type": "object",\n  "properties": {}\n}'}
											error={jsonFieldErrors.input_schema}
											onValueChange={setJsonValue}
											onError={setJsonFieldError}
											onClear={clearJsonFieldError}
										/>
										<JsonEditor
											field="output_schema"
											value={formOutputSchema}
											label="Output schema"
											description="Expected output shape returned by this skill."
											rows={7}
											placeholder={'{\n  "type": "object",\n  "properties": {}\n}'}
											error={jsonFieldErrors.output_schema}
											onValueChange={setJsonValue}
											onError={setJsonFieldError}
											onClear={clearJsonFieldError}
										/>
										<JsonEditor
											field="credential_schema"
											value={formCredentialSchema}
											label="Credential schema"
											description="Credential fields required before activation."
											rows={7}
											placeholder={'{\n  "required": []\n}'}
											error={jsonFieldErrors.credential_schema}
											onValueChange={setJsonValue}
											onError={setJsonFieldError}
											onClear={clearJsonFieldError}
										/>
									</div>
								{/if}
							</div>
						</div>
					</div>
				{/if}

				{#if jsonError}
					<div class="rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-2">
						<p class="text-xs text-red-400">{jsonError}</p>
					</div>
				{/if}
			</div>
		</div>

		<div class="flex shrink-0 items-center justify-between gap-2 border-t bg-background px-5 py-3">
			<div>
				{#if mode === 'edit'}
					<Button
						variant="destructive"
						size="sm"
						onclick={() => (deleteConfirm = true)}
						disabled={busy}
					>
						<Trash2 data-icon="inline-start" />
						Delete
					</Button>
				{/if}
			</div>
			<div class="flex items-center gap-2">
				<Button variant="ghost" size="sm" onclick={() => (open = false)} disabled={busy}
					>Cancel</Button
				>
				<Button size="sm" disabled={busy} onclick={handleSave}>
					{#if busy}
						<Spinner data-icon="inline-start" />
						{mode === 'create' ? 'Creating...' : 'Saving...'}
					{:else}
						{mode === 'create' ? 'Create' : 'Save'}
					{/if}
				</Button>
			</div>
		</div>
	</Dialog.Content>
</Dialog.Root>

<AlertDialog.Root bind:open={deleteConfirm}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Delete {entityType === 'tool' ? 'Tool' : 'Skill'}</AlertDialog.Title>
			<AlertDialog.Description>
				Delete "{editingItem?.slug}"? This is permanent and cannot be undone.
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>Cancel</AlertDialog.Cancel>
			<AlertDialog.Action onclick={onDelete}>Delete</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
