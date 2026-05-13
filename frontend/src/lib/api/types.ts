// ─── Envelope ────────────────────────────────────────────────────────────────

export interface ApiResponse<T> {
	status: 'success';
	data: T;
	message?: string;
	meta?: Record<string, unknown>;
}

export interface ApiErrorBody {
	code: string;
	message: string;
	details?: unknown;
}

export interface ApiErrorPayload {
	status: 'error';
	error: ApiErrorBody;
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface LoginRequest {
	email: string;
	password: string;
}

export interface RegisterRequest {
	email: string;
	password: string;
	name: string;
}

export interface LogoutRequest {
	refresh_token: string;
}

export interface RefreshRequest {
	refresh_token: string;
}

export interface AuthResponse {
	access_token: string | null;
	refresh_token: string | null;
	token_type: string;
	user_id: string;
	email: string;
	awaiting_assignment: boolean;
	memberships: TenantAccessResponse[];
}

export interface AuthMeResponse {
	id: string;
	email: string;
	name: string;
	status: string;
	is_superadmin: boolean;
}

export interface TenantAccessResponse {
	tenant_id: string;
	tenant_slug: string;
	tenant_name: string;
	role: string;
	status: string;
}

export interface AccountActivationRequest {
	email: string;
}

export interface AccountActivationConfirmRequest {
	token: string;
}

export interface PasswordForgotRequest {
	email: string;
}

export interface PasswordResetRequest {
	token: string;
	new_password: string;
}

export interface PasswordChangeRequest {
	current_password: string;
	new_password: string;
}

// ─── System settings ─────────────────────────────────────────────────────────

export interface PublicSystemSettingsResponse {
	platform_name: string;
	platform_public_url: string;
	platform_logo_url: string;
	maintenance_mode: boolean;
	registration_enabled: boolean;
	public_settings: Record<string, unknown>;
}

export interface SystemSettingsResponse extends PublicSystemSettingsResponse {
	smtp_host: string;
	smtp_port: number;
	smtp_secure: boolean;
	smtp_user: string;
	smtp_from: string;
	has_smtp_pass: boolean;
	ai_provider: string;
	ai_default_model: string;
	has_ai_api_key: boolean;
	custom_settings: Record<string, unknown>;
	updated_by: string;
}

export interface SystemSettingsUpdateRequest {
	platform_name?: string;
	platform_public_url?: string;
	platform_logo_url?: string;
	maintenance_mode?: boolean;
	registration_enabled?: boolean;
	smtp_host?: string;
	smtp_port?: number;
	smtp_secure?: boolean;
	smtp_user?: string;
	smtp_pass?: string;
	smtp_from?: string;
	ai_provider?: string;
	ai_api_key?: string;
	ai_default_model?: string;
	custom_settings?: Record<string, unknown>;
	public_settings?: Record<string, unknown>;
}

// ─── Agent instances ──────────────────────────────────────────────────────────

export interface AgentInstanceResponse {
	id: string;
	tenant_id: string;
	name: string;
	description: string;
	core_prompt: string;
	model: string;
	temperature: number;
	status: string;
	rag_scope: string[];
	created_by: string;
}

export interface AgentInstanceCreateRequest {
	name: string;
	description?: string;
	core_prompt: string;
	model: string;
	temperature: number;
	rag_scope?: string[];
}

export interface AgentInstanceUpdateRequest {
	name?: string;
	description?: string;
	core_prompt?: string;
	model?: string;
	temperature?: number;
	status?: string;
	rag_scope?: string[];
}

// ─── Prompt config ────────────────────────────────────────────────────────────

export interface AgentInstructionBlock {
	id?: string;
	topic: string;
	title: string;
	content: string;
	priority: number;
	is_enabled: boolean;
}

export interface AgentGuardrail {
	id?: string;
	category: string;
	rule: string;
	severity: string;
	is_enabled: boolean;
	metadata?: Record<string, unknown>;
}

export interface AgentConstraint {
	id?: string;
	rule: string;
	priority: number;
	is_enabled: boolean;
}

export interface AgentPromptConfigRequest {
	instruction_blocks: AgentInstructionBlock[];
	guardrails: AgentGuardrail[];
	constraints: AgentConstraint[];
}

export interface AgentPromptConfigResponse {
	tenant_id: string;
	instance_id: string;
	instruction_blocks: AgentInstructionBlock[];
	guardrails: AgentGuardrail[];
	constraints: AgentConstraint[];
}

// ─── Registry ─────────────────────────────────────────────────────────────────

export interface ActivationRequest {
	is_enabled: boolean;
	config?: Record<string, unknown>;
}

export interface SkillActivationResponse {
	slug: string;
	name: string;
	description: string | null;
	category: string | null;
	prompt_block: string;
	tool_schema: Record<string, unknown>;
	executor: string;
	input_schema: Record<string, unknown>;
	output_schema: Record<string, unknown>;
	requires_credential: boolean;
	credential_schema?: Record<string, unknown>;
	config: Record<string, unknown>;
}

export interface ToolVariableSpec {
	name: string;
	label?: string;
	description?: string;
	type?: string;
	required?: boolean;
	default?: unknown;
	secret?: boolean;
}

export interface ToolActivationResponse {
	slug: string;
	name: string;
	description: string | null;
	category: string | null;
	prompt_block: string;
	schema: Record<string, unknown>;
	executor: string;
	is_builtin: boolean;
	method?: string;
	endpoint?: string | null;
	headers_template?: Record<string, string>;
	body_template?: string | null;
	variables_schema?: ToolVariableSpec[];
	config: Record<string, unknown>;
}

export interface ToolMetadataResponse {
	tenant_id: string;
	instance_id: string;
	skills: SkillActivationResponse[];
	tools: ToolActivationResponse[];
}

export interface CatalogSkillResponse {
	slug: string;
	name: string;
	description: string | null;
	category: string | null;
	requires_credential: boolean;
}

export interface CatalogToolResponse {
	slug: string;
	name: string;
	description: string | null;
	category: string | null;
}

export interface RegistryCatalogResponse {
	skills: CatalogSkillResponse[];
	tools: CatalogToolResponse[];
}

export interface CredentialResponse {
	id: string;
	tenant_id: string;
	skill_id: string;
	skill_slug: string;
	secret_ref: string;
	metadata: Record<string, unknown>;
}

export interface CredentialRequest {
	secret_ref: string;
	metadata?: Record<string, unknown>;
}

export interface SkillDefinitionResponse {
	id: string;
	slug: string;
	name: string;
	description: string;
	category: string;
	prompt_block: string;
	tool_schema: Record<string, unknown>;
	executor: string;
	input_schema: Record<string, unknown>;
	output_schema: Record<string, unknown>;
	requires_credential: boolean;
	credential_schema: Record<string, unknown>;
	is_active: boolean;
}

export interface SkillDefinitionRequest {
	slug: string;
	name: string;
	description: string;
	category: string;
	prompt_block?: string;
	tool_schema?: Record<string, unknown>;
	executor?: string;
	input_schema?: Record<string, unknown>;
	output_schema?: Record<string, unknown>;
	requires_credential?: boolean;
	credential_schema?: Record<string, unknown>;
	is_active?: boolean;
}

export interface ToolDefinitionResponse {
	id: string;
	slug: string;
	name: string;
	description: string;
	category: string;
	prompt_block: string;
	schema: Record<string, unknown>;
	executor: string;
	is_builtin: boolean;
}

export interface ToolDefinitionRequest {
	slug: string;
	name: string;
	description: string;
	category: string;
	prompt_block?: string;
	schema?: Record<string, unknown>;
	executor?: string;
	is_builtin?: boolean;
}

// ─── Members ──────────────────────────────────────────────────────────────────

export interface TenantMemberResponse {
	user_id: string;
	email: string;
	name: string;
	role: string;
	status: string;
}

export interface TenantMemberUpdateRequest {
	role?: string;
	status?: string;
}

// ─── Invitations ──────────────────────────────────────────────────────────────

export interface TenantInvitationResponse {
	id: string;
	tenant_id: string;
	email: string;
	role: string;
	status: string;
	expires_at: string;
	accepted_at: string | null;
	created_at: string;
}

export interface TenantInvitationCreateRequest {
	email: string;
	role: string;
}

export interface TenantInvitationValidateRequest {
	token: string;
}

export interface TenantInvitationPublicResponse {
	tenant_id: string;
	tenant_name: string;
	email: string;
	role: string;
	status: string;
	expires_at: string;
}

export interface TenantInvitationAcceptRequest {
	token: string;
	email: string;
	name: string;
	password: string;
}

export interface TenantInvitationAcceptResponse {
	user_id: string;
	tenant_id: string;
	email: string;
	role: string;
	membership_status: string;
}

// ─── AI settings ─────────────────────────────────────────────────────────────

export interface ProviderInfo {
	name: string;
	enabled: boolean;
	has_api_key: boolean;
	api_key_hint: string | null;
	configured_at: string | null;
	configured_by: string | null;
}

export interface TenantProvidersResponse {
	tenant_id: string;
	providers: ProviderInfo[];
}

export interface ProviderConfigRequest {
	name: string;
	api_key?: string;
	enabled?: boolean;
}

export interface ProviderModelInfo {
	id: string;
}

export interface ProviderModelsResponse {
	provider: string;
	models: ProviderModelInfo[];
}

// ─── Collections ─────────────────────────────────────────────────────────────

export interface CollectionResponse {
	id: string;
	tenant_id: string;
	name: string;
	description: string;
	indexing_status: string;
	indexing_progress: number;
	document_count: number;
	indexed_count: number;
	failed_count: number;
	last_indexed_at: string | null;
	created_at: string;
}

export interface CollectionCreateRequest {
	name: string;
	description?: string;
}

export interface CollectionUpdateRequest {
	name?: string;
	description?: string;
}

export interface DocumentResponse {
	id: string;
	tenant_id: string;
	collection_id: string;
	filename: string;
	source_type: string;
	status: string;
	chunk_count: number;
	error_message: string | null;
	content_type: string | null;
	size_bytes: number | null;
	created_at: string;
	indexed_at: string | null;
}

// ─── Versions ──────────────────────────────────────────────────

export interface VersionEntry {
	id: string;
	version: number;
	action: string;
	changed_by: string | null;
	actor_type: string;
	actor_role: string | null;
	snapshot: Record<string, unknown>;
	metadata: Record<string, unknown>;
	created_at: string | null;
}

// ─── Superadmin ───────────────────────────────────────────────────────────────

export interface SuperadminTenantResponse {
	id: string;
	slug: string;
	name: string;
	plan: string;
	status: string;
	settings: Record<string, unknown>;
}

export interface SuperadminTenantCreateRequest {
	slug: string;
	name: string;
	plan: string;
	status: string;
	settings?: Record<string, unknown>;
}

export interface SuperadminTenantUpdateRequest {
	name?: string;
	plan?: string;
	status?: string;
	settings?: Record<string, unknown>;
}

export interface SuperadminUserResponse {
	id: string;
	email: string;
	name: string;
	status: string;
	is_superadmin: boolean;
}

export interface SuperadminUserUpdateRequest {
	name?: string;
	status?: string;
	is_superadmin?: boolean;
}

export interface SuperadminAgentInstanceResponse {
	id: string;
	name: string;
	description: string | null;
	model: string;
	status: string;
}

export interface SuperadminAuditLogResponse {
	id: string;
	user_id: string | null;
	user_email: string | null;
	user_name: string | null;
	action: string;
	resource: string;
	resource_id: string | null;
	actor_type: string;
	actor_role: string | null;
	created_at: string;
	metadata: Record<string, unknown>;
}

export interface EmailTemplateResponse {
	id: string;
	slug: string;
	name: string;
	description: string;
	subject_template: string;
	body_template: string;
	body_format: string;
	variables_schema: Record<string, unknown>;
	is_active: boolean;
}

export interface EmailTemplateRequest {
	slug: string;
	name: string;
	description?: string;
	subject_template: string;
	body_template: string;
	body_format?: string;
	variables_schema?: Record<string, unknown>;
	is_active?: boolean;
}

export interface MessageResponse {
	message: string;
}

// ─── Chat / Agent runtime ─────────────────────────────────────────────────────

export interface ChatRequest {
	message: string;
	session_id?: string | null;
	channel?: string;
	metadata?: Record<string, unknown>;
}

export type ChatEventName =
	| 'message.persisted'
	| 'assistant.delta'
	| 'run.trace'
	| 'run.completed';

export interface ChatEvent {
	event: ChatEventName | string;
	session_id: string;
	sequence_no?: number | null;
	content?: string | null;
	metadata?: Record<string, unknown>;
}

export interface RunTraceSection {
	label: string;
	content: string;
}

export interface RunTraceChunk {
	text: string;
	source?: string | null;
	score?: number | null;
	collection_id?: string | null;
	document_id?: string | null;
	filename?: string | null;
}

export interface RunTraceToolCall {
	id?: string | null;
	name?: string | null;
	arguments?: unknown;
}

export interface RunTraceToolResult {
	id?: string | null;
	name?: string | null;
	output?: unknown;
	error?: string | null;
}

export interface RunTraceTokenCall {
	prompt_tokens: number;
	completion_tokens: number;
	total_tokens: number;
	model?: string | null;
	phase?: string | null;
	iteration?: number | null;
}

export interface RunTraceTokenUsage {
	prompt_tokens: number;
	completion_tokens: number;
	total_tokens: number;
	llm_calls: number;
	embedding_tokens: number;
	embedding_calls: number;
	per_call: RunTraceTokenCall[];
}

export interface RunTraceExecutedCall {
	id?: string | null;
	name?: string | null;
	kind: 'tool' | 'skill';
	arguments?: unknown;
	output?: unknown;
	error?: string | null;
	iteration?: number | null;
}

export interface RunTracePayload {
	run_id: string;
	tenant_id: string;
	instance_id: string;
	session_id: string;
	channel: string;
	user_message: string;
	final_response: string;
	model?: string | null;
	temperature?: number | null;
	ai_provider?: string | null;
	system_prompt: string;
	system_prompt_sections: RunTraceSection[];
	available_tools: string[];
	available_skills: string[];
	tool_schemas: unknown[];
	linked_agents: unknown[];
	rag_scope: string[];
	retrieved_chunks: RunTraceChunk[];
	pending_tool_calls: RunTraceToolCall[];
	tool_results: RunTraceToolResult[];
	executed_tool_calls: RunTraceExecutedCall[];
	token_usage?: RunTraceTokenUsage;
	rag_error?: string | null;
	run_error?: string | null;
	handoff_target?: string | null;
	handoff_summary?: string | null;
	citations: unknown[];
	node_timings: { name: string; duration_ms: number }[];
	started_at: string;
	completed_at: string;
	duration_ms: number;
}

export interface RunTraceResponse {
	run_id: string;
	tenant_id: string;
	instance_id: string;
	session_id: string;
	channel: string;
	trace: RunTracePayload;
	started_at: string;
	completed_at: string;
	created_at: string;
}

export interface RunTraceListItem {
	run_id: string;
	instance_id: string;
	session_id: string;
	started_at: string;
	completed_at: string;
	duration_ms: number;
	user_message?: string | null;
	final_response_preview?: string | null;
	total_tokens?: number | null;
	prompt_tokens?: number | null;
	completion_tokens?: number | null;
	embedding_tokens?: number | null;
	embedding_calls?: number | null;
}
