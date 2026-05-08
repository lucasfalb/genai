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

export interface AgentPromptConfigRequest {
	instruction_blocks: AgentInstructionBlock[];
	guardrails: AgentGuardrail[];
}

export interface AgentPromptConfigResponse {
	tenant_id: string;
	instance_id: string;
	instruction_blocks: AgentInstructionBlock[];
	guardrails: AgentGuardrail[];
}

// ─── Registry ─────────────────────────────────────────────────────────────────

export interface ActivationRequest {
	is_enabled: boolean;
	config?: Record<string, unknown>;
}

export interface SkillActivationResponse {
	id: string;
	tenant_id: string;
	instance_id: string;
	skill_id: string;
	skill_slug: string;
	is_enabled: boolean;
	config: Record<string, unknown>;
}

export interface ToolActivationResponse {
	id: string;
	tenant_id: string;
	instance_id: string;
	tool_id: string;
	tool_slug: string;
	is_enabled: boolean;
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

export interface TenantAIConfigResponse {
	tenant_id: string;
	provider: string | null;
	default_model: string | null;
	enabled: boolean;
	has_api_key: boolean;
	configured_by: string | null;
}

export interface TenantAIConfigRequest {
	provider: string;
	api_key: string;
	default_model: string | null;
	enabled: boolean;
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
	storage_path: string | null;
	content_type: string | null;
	size_bytes: number | null;
	created_at: string;
	indexed_at: string | null;
}

// ─── Chat ─────────────────────────────────────────────────────────────────────

export interface ChatRequest {
	message: string;
	session_id?: string;
	channel?: string;
	metadata?: Record<string, unknown>;
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
	action: string;
	resource: string;
	resource_id: string | null;
	actor_type: string;
	actor_role: string | null;
	created_at: string;
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
