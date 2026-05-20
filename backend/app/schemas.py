from datetime import datetime
from typing import Any, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

ResponseDataT = TypeVar("ResponseDataT")


class ApiResponse(BaseModel, Generic[ResponseDataT]):
    status: Literal["success"] = "success"
    message: str | None = None
    data: ResponseDataT | None = None
    meta: dict = Field(default_factory=dict)


class ApiError(BaseModel):
    code: str
    message: str
    details: object | None = None


class ApiErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    error: ApiError


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class PasswordForgotRequest(BaseModel):
    email: EmailStr


class PasswordResetRequest(BaseModel):
    token: str = Field(min_length=16, max_length=512)
    new_password: str = Field(min_length=8, max_length=128)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class AccountActivationRequest(BaseModel):
    email: EmailStr


class AccountActivationConfirmRequest(BaseModel):
    token: str = Field(min_length=16, max_length=512)


class MessageResponse(BaseModel):
    message: str


class MembershipResponse(BaseModel):
    tenant_id: UUID
    role: str


class AuthResponse(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    user_id: UUID
    email: EmailStr
    awaiting_assignment: bool = False
    memberships: list[MembershipResponse] = []


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    name: str | None
    status: str


class AuthMeResponse(BaseModel):
    id: UUID
    email: EmailStr
    name: str | None
    status: str
    is_superadmin: bool


class TenantAccessResponse(BaseModel):
    tenant_id: UUID
    tenant_slug: str
    tenant_name: str
    role: str
    status: str


class SuperadminTenantCreateRequest(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9-]+$", max_length=120)
    name: str = Field(min_length=1, max_length=160)
    plan: str = Field(default="starter", pattern=r"^[a-z0-9_-]+$", max_length=80)
    status: str = Field(default="active", pattern=r"^(active|suspended|archived)$")
    settings: dict = Field(default_factory=dict)


class SuperadminTenantUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    plan: str | None = Field(default=None, pattern=r"^[a-z0-9_-]+$", max_length=80)
    status: str | None = Field(default=None, pattern=r"^(active|suspended|archived)$")
    settings: dict | None = None


class SuperadminTenantResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    plan: str
    status: str
    settings: dict


class SuperadminUserUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    status: str | None = Field(default=None, pattern=r"^(pending|active|suspended)$")
    is_superadmin: bool | None = None


class SuperadminUserResponse(BaseModel):
    id: UUID
    email: EmailStr
    name: str | None
    status: str
    is_superadmin: bool


class SuperadminAgentInstanceResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    model: str
    status: str


class SuperadminAuditLogResponse(BaseModel):
    id: UUID
    user_id: UUID | None
    user_email: str | None
    user_name: str | None
    action: str
    resource: str
    resource_id: str | None
    actor_type: str
    actor_role: str | None
    created_at: datetime
    metadata: dict


class TenantMemberUpdateRequest(BaseModel):
    role: str | None = Field(default=None, pattern=r"^(tenant_admin|member|viewer)$")
    status: str | None = Field(default=None, pattern=r"^(active|pending|suspended)$")


class SuperadminMemberAddRequest(BaseModel):
    email: str = Field(min_length=1, max_length=254)
    role: str = Field(default="member", pattern=r"^(tenant_admin|member|viewer)$")


class TenantMemberResponse(BaseModel):
    user_id: UUID
    email: EmailStr
    name: str | None
    role: str
    status: str


class TenantInvitationCreateRequest(BaseModel):
    email: EmailStr
    role: str = Field(pattern=r"^(tenant_admin|member|viewer)$")


class TenantInvitationValidateRequest(BaseModel):
    token: str = Field(min_length=16, max_length=512)


class TenantInvitationAcceptRequest(BaseModel):
    token: str = Field(min_length=16, max_length=512)
    email: EmailStr
    name: str | None = Field(default=None, max_length=120)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class TenantInvitationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    email: EmailStr
    role: str
    status: str
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime


class TenantInvitationPublicResponse(BaseModel):
    tenant_id: UUID
    tenant_name: str
    email: EmailStr
    role: str
    status: str
    expires_at: datetime


class TenantInvitationAcceptResponse(BaseModel):
    user_id: UUID
    tenant_id: UUID
    email: EmailStr
    role: str
    membership_status: str


class EmailTemplateRequest(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9_]+$", max_length=80)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    subject_template: str = Field(min_length=1)
    body_template: str = Field(min_length=1)
    body_format: str = Field(default="html", pattern=r"^(html|text)$")
    variables_schema: dict = Field(default_factory=dict)
    is_active: bool = True


class EmailTemplateResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str | None
    subject_template: str
    body_template: str
    body_format: str
    variables_schema: dict
    is_active: bool


class SkillDefinitionRequest(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9_]+$", max_length=100)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    category: str | None = Field(default=None, max_length=80)
    prompt_block: str = Field(min_length=1)
    tool_schema: dict = Field(default_factory=dict)
    executor: str = Field(min_length=1, max_length=240)
    input_schema: dict = Field(default_factory=dict)
    output_schema: dict = Field(default_factory=dict)
    requires_credential: bool = False
    credential_schema: dict | None = None
    is_active: bool = True


class SkillDefinitionResponse(SkillDefinitionRequest):
    id: UUID


class ToolDefinitionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    slug: str = Field(pattern=r"^[a-z0-9_]+$", max_length=100)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    category: str | None = Field(default=None, max_length=80)
    prompt_block: str = Field(min_length=1)
    schema_: dict = Field(default_factory=dict, alias="schema", serialization_alias="schema")
    executor: str = Field(min_length=1, max_length=240)
    is_builtin: bool = False
    method: str = Field(default="GET", pattern=r"^(GET|POST|PUT|PATCH|DELETE)$")
    endpoint: str | None = None
    headers_template: dict = Field(default_factory=dict)
    body_template: str | None = None
    variables_schema: list[dict] = Field(default_factory=list)


class ToolDefinitionResponse(ToolDefinitionRequest):
    id: UUID


class ActivationRequest(BaseModel):
    is_enabled: bool = True
    config: dict = Field(default_factory=dict)


class ToolTestRequest(BaseModel):
    config: dict = Field(default_factory=dict)
    arguments: dict = Field(default_factory=dict)


class ToolTestResponse(BaseModel):
    name: str
    status: int | None = None
    data: Any | None = None
    error: str | None = None
    raw: dict = Field(default_factory=dict)


class SkillActivationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    instance_id: UUID
    skill_id: UUID
    skill_slug: str
    is_enabled: bool
    config: dict


class ToolActivationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    instance_id: UUID
    tool_id: UUID
    tool_slug: str
    is_enabled: bool
    config: dict


class CredentialRequest(BaseModel):
    secret_ref: str = Field(min_length=1, max_length=500)
    metadata: dict = Field(default_factory=dict)


class CredentialResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    skill_id: UUID
    skill_slug: str
    secret_ref: str
    metadata: dict


class RegistrySkillMetadata(BaseModel):
    slug: str
    name: str
    description: str | None
    category: str | None
    prompt_block: str
    tool_schema: dict
    executor: str
    input_schema: dict
    output_schema: dict
    requires_credential: bool
    credential_schema: dict | None = None
    config: dict


class RegistryToolMetadata(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    slug: str
    name: str
    description: str | None
    category: str | None
    prompt_block: str
    schema_: dict = Field(alias="schema", serialization_alias="schema")
    executor: str
    is_builtin: bool
    method: str = "GET"
    endpoint: str | None = None
    headers_template: dict = Field(default_factory=dict)
    body_template: str | None = None
    variables_schema: list[dict] = Field(default_factory=list)
    config: dict


class ToolMetadataResponse(BaseModel):
    tenant_id: UUID
    instance_id: UUID
    skills: list[RegistrySkillMetadata]
    tools: list[RegistryToolMetadata]


class AgentLinkContextPolicy(BaseModel):
    include_recent_messages: bool = True
    max_messages: int = Field(default=8, ge=0, le=50)
    include_handoff_summary: bool = True
    include_source_agent_name: bool = True


class AgentLinkCreateRequest(BaseModel):
    target_instance_id: UUID
    transfer_tool_name: str = Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_]{1,79}$", max_length=80)
    trigger_description: str = Field(min_length=1, max_length=1200)
    handoff_instructions: str | None = Field(default=None, max_length=4000)
    context_policy: AgentLinkContextPolicy = Field(default_factory=AgentLinkContextPolicy)
    transfer_mode: Literal["llm_decision", "router_classifier"] = "llm_decision"
    is_enabled: bool = True

    @model_validator(mode="after")
    def reject_sensitive_text(self):
        _reject_prompt_config_secrets(self.trigger_description)
        if self.handoff_instructions:
            _reject_prompt_config_secrets(self.handoff_instructions)
        return self


class AgentLinkUpdateRequest(BaseModel):
    transfer_tool_name: str | None = Field(default=None, pattern=r"^[a-zA-Z_][a-zA-Z0-9_]{1,79}$", max_length=80)
    trigger_description: str | None = Field(default=None, min_length=1, max_length=1200)
    handoff_instructions: str | None = Field(default=None, max_length=4000)
    context_policy: AgentLinkContextPolicy | None = None
    transfer_mode: Literal["llm_decision", "router_classifier"] | None = None
    is_enabled: bool | None = None

    @model_validator(mode="after")
    def reject_sensitive_text(self):
        if self.trigger_description:
            _reject_prompt_config_secrets(self.trigger_description)
        if self.handoff_instructions:
            _reject_prompt_config_secrets(self.handoff_instructions)
        return self


class AgentLinkResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    source_instance_id: UUID
    target_instance_id: UUID
    target_name: str
    target_description: str | None = None
    transfer_tool_name: str
    trigger_description: str
    handoff_instructions: str | None = None
    context_policy: AgentLinkContextPolicy
    transfer_mode: Literal["llm_decision", "router_classifier"]
    is_enabled: bool
    created_at: datetime
    updated_at: datetime | None = None


class DocumentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    collection_id: UUID
    filename: str
    source_type: str
    status: str
    chunk_count: int
    error_message: str | None
    content_type: str | None = None
    size_bytes: int | None = None
    created_at: datetime
    indexed_at: datetime | None


class DocumentCreateRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)


class DocumentContentUpdateRequest(BaseModel):
    content: str = Field(min_length=1)


class DocumentContentURLResponse(BaseModel):
    url: str
    content_type: str
    expires_in: int


class CatalogSkillResponse(BaseModel):
    slug: str
    name: str
    description: str | None
    category: str | None
    requires_credential: bool


class CatalogToolResponse(BaseModel):
    slug: str
    name: str
    description: str | None
    category: str | None


class RegistryCatalogResponse(BaseModel):
    skills: list[CatalogSkillResponse]
    tools: list[CatalogToolResponse]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=16000)
    session_id: UUID | None = None
    channel: str = Field(default="api", pattern=r"^[a-z0-9_:-]+$", max_length=80)
    metadata: dict = Field(default_factory=dict)


class ChatEvent(BaseModel):
    event: str
    session_id: UUID
    sequence_no: int | None = None
    content: str | None = None
    metadata: dict = Field(default_factory=dict)


class SessionListItem(BaseModel):
    id: UUID
    instance_id: UUID
    channel: str
    user_ref: str | None = None
    started_at: datetime
    last_message_at: datetime | None = None
    message_count: int
    is_live: bool = False
    environment: dict[str, Any] | None = None


class SessionMessageItem(BaseModel):
    id: UUID
    session_id: UUID
    sequence_no: int
    role: str
    content: str


class RunTraceSection(BaseModel):
    label: str
    content: str


class RunTraceResponse(BaseModel):
    run_id: UUID
    tenant_id: UUID
    instance_id: UUID
    session_id: UUID
    channel: str
    trace: dict
    started_at: datetime
    completed_at: datetime
    created_at: datetime


class RunTraceListItem(BaseModel):
    run_id: UUID
    instance_id: UUID
    session_id: UUID
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    user_message: str | None = None
    final_response_preview: str | None = None
    total_tokens: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    embedding_tokens: int | None = None
    embedding_calls: int | None = None


class SystemSettingsUpdateRequest(BaseModel):
    platform_name: str | None = Field(default=None, min_length=1, max_length=160)
    platform_public_url: str | None = Field(default=None, max_length=512)
    platform_logo_url: str | None = Field(default=None, max_length=512)
    maintenance_mode: bool | None = None
    registration_enabled: bool | None = None
    smtp_host: str | None = Field(default=None, max_length=255)
    smtp_port: int | None = Field(default=None, ge=1, le=65535)
    smtp_secure: bool | None = None
    smtp_user: str | None = Field(default=None, max_length=255)
    smtp_pass: str | None = Field(default=None, min_length=1, max_length=512)
    smtp_from: str | None = Field(default=None, max_length=255)
    ai_provider: str | None = Field(default=None, pattern=r"^[a-z0-9_-]+$", max_length=80)
    ai_api_key: str | None = Field(default=None, min_length=1, max_length=512)
    ai_default_model: str | None = Field(default=None, max_length=120)
    custom_settings: dict[str, Any] | None = None
    public_settings: dict[str, Any] | None = None


class SystemSettingsResponse(BaseModel):
    platform_name: str
    platform_public_url: str | None
    platform_logo_url: str | None
    maintenance_mode: bool
    registration_enabled: bool
    smtp_host: str | None
    smtp_port: int
    smtp_secure: bool
    smtp_user: str | None
    smtp_from: str | None
    has_smtp_pass: bool
    ai_provider: str
    ai_default_model: str
    has_ai_api_key: bool
    custom_settings: dict[str, Any]
    public_settings: dict[str, Any]
    updated_by: UUID | None


class PublicSystemSettingsResponse(BaseModel):
    platform_name: str
    platform_public_url: str | None
    platform_logo_url: str | None
    maintenance_mode: bool
    registration_enabled: bool
    public_settings: dict[str, Any]


class ProviderConfigRequest(BaseModel):
    name: str = Field(pattern=r"^[a-z0-9_-]+$", max_length=80)
    api_key: str | None = Field(default=None, min_length=1, max_length=512)
    enabled: bool | None = None


class ProviderInfo(BaseModel):
    name: str
    enabled: bool
    has_api_key: bool
    api_key_hint: str | None = None
    configured_at: datetime | None
    configured_by: str | None


class TenantProvidersResponse(BaseModel):
    tenant_id: str
    providers: list[ProviderInfo]


class TenantAIConfigRequest(BaseModel):
    provider: str = Field(pattern=r"^[a-z0-9_-]+$", max_length=80)
    api_key: str = Field(min_length=1, max_length=512)
    default_model: str | None = Field(default=None, max_length=120)
    enabled: bool = True


class TenantAIConfigResponse(BaseModel):
    tenant_id: UUID
    provider: str | None
    default_model: str | None
    enabled: bool
    has_api_key: bool
    configured_by: UUID | None = None


class ProviderModelInfo(BaseModel):
    id: str


class ProviderModelsResponse(BaseModel):
    provider: str
    models: list[ProviderModelInfo]


class VersionEntryResponse(BaseModel):
    id: str
    version: int
    action: str
    changed_by: str | None = None
    actor_type: str
    actor_role: str | None = None
    snapshot: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    created_at: str | None = None


class AgentInstanceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    core_prompt: str = Field(min_length=1)
    model: str = Field(default="gpt-5-mini", max_length=120)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    rag_scope: list = Field(default_factory=list)


class AgentInstanceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    core_prompt: str | None = Field(default=None, min_length=1)
    model: str | None = Field(default=None, max_length=120)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    status: str | None = Field(default=None, pattern=r"^(active|inactive)$")
    rag_scope: list | None = None


class AgentInstructionBlock(BaseModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    topic: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_. -]+$")
    title: str = Field(min_length=0, max_length=160)
    content: str = Field(min_length=1, max_length=4000)
    priority: int = Field(default=100, ge=0, le=1000)
    is_enabled: bool = True

    @field_validator("content")
    @classmethod
    def reject_sensitive_content(cls, value: str) -> str:
        _reject_prompt_config_secrets(value)
        return value


class AgentGuardrail(BaseModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    category: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_. -]+$")
    rule: str = Field(min_length=1, max_length=2000)
    severity: Literal["info", "warning", "critical", "blocking"] = "critical"
    is_enabled: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("rule")
    @classmethod
    def reject_sensitive_rule(cls, value: str) -> str:
        _reject_prompt_config_secrets(value)
        return value

    @model_validator(mode="after")
    def reject_sensitive_metadata(self):
        _reject_sensitive_dict(self.metadata)
        return self


class AgentConstraint(BaseModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    rule: str = Field(min_length=1, max_length=2000)
    priority: int = Field(default=100, ge=0, le=1000)
    is_enabled: bool = True

    @field_validator("rule")
    @classmethod
    def reject_sensitive_rule(cls, value: str) -> str:
        _reject_prompt_config_secrets(value)
        return value


class AgentPromptConfigRequest(BaseModel):
    instruction_blocks: list[AgentInstructionBlock] = Field(default_factory=list, max_length=50)
    guardrails: list[AgentGuardrail] = Field(default_factory=list, max_length=50)
    constraints: list[AgentConstraint] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def reject_duplicate_ids(self):
        instruction_ids = [item.id for item in self.instruction_blocks]
        guardrail_ids = [item.id for item in self.guardrails]
        constraint_ids = [item.id for item in self.constraints]
        if len(instruction_ids) != len(set(instruction_ids)):
            raise ValueError("Duplicate instruction block ids are not allowed")
        if len(guardrail_ids) != len(set(guardrail_ids)):
            raise ValueError("Duplicate guardrail ids are not allowed")
        if len(constraint_ids) != len(set(constraint_ids)):
            raise ValueError("Duplicate constraint ids are not allowed")
        return self


class AgentPromptConfigResponse(BaseModel):
    tenant_id: UUID
    instance_id: UUID
    instruction_blocks: list[AgentInstructionBlock]
    guardrails: list[AgentGuardrail]
    constraints: list[AgentConstraint] = Field(default_factory=list)


class AgentInstanceResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    core_prompt: str
    model: str
    temperature: float
    status: str
    rag_scope: list
    created_by: UUID


class CollectionCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None


class CollectionUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None


class CollectionResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    indexing_status: str
    indexing_progress: float
    document_count: int
    indexed_count: int
    failed_count: int
    last_indexed_at: datetime | None
    created_at: datetime


# --- Channel Config ---

class WebWidgetConfig(BaseModel):
    title: str = "Chat with us"
    subtitle: str = ""
    bot_name: str = "Assistant"
    avatar_mode: Literal["initials", "icon", "image"] = "initials"
    avatar_icon: str = Field(default="bot", max_length=80)
    avatar_image_url: str | None = None
    primary_color: str = "#3b82f6"
    bg_color: str = "#ffffff"
    border_radius: Literal["sharp", "rounded", "full"] = "rounded"
    position: Literal["bottom-right", "bottom-left"] = "bottom-right"
    font_family: str = Field(default="system", max_length=120)
    locale: str = Field(default="en-US", max_length=20)
    launcher_mode: Literal["icon", "image"] = "icon"
    launcher_icon: str = Field(default="message-circle", max_length=80)
    launcher_image_url: str | None = None
    auto_open_delay: int | None = None
    show_unread_badge: bool = True
    opening_message: str | None = None
    quick_replies: list[str] = Field(default_factory=list)
    sound_enabled: bool = False
    typing_indicator: bool = True
    mobile_fullscreen: bool = True
    ui_messages: dict[str, Any] = Field(default_factory=dict)


class ChannelConfigResponse(BaseModel):
    id: str
    channel: str
    is_active: bool
    config: dict
    allowed_origins: list[str]
    created_at: str


class ChannelConfigUpdateRequest(BaseModel):
    config: WebWidgetConfig = Field(default_factory=WebWidgetConfig)
    allowed_origins: list[str] = Field(default_factory=list)
    is_active: bool | None = None


_PROMPT_CONFIG_SECRET_MARKERS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer ",
    "password",
    "secret",
    "smtp_pass",
    "token",
)


def _reject_prompt_config_secrets(value: str) -> None:
    normalized = value.lower()
    if any(marker in normalized for marker in _PROMPT_CONFIG_SECRET_MARKERS):
        raise ValueError("Prompt configuration cannot contain secrets or credential material")


def _reject_sensitive_dict(payload: dict[str, Any]) -> None:
    for key, value in payload.items():
        normalized_key = key.lower().replace("-", "_")
        if any(marker.strip() in normalized_key for marker in _PROMPT_CONFIG_SECRET_MARKERS):
            raise ValueError(f"Sensitive metadata key is not allowed: {key}")
        if isinstance(value, str):
            _reject_prompt_config_secrets(value)
        elif isinstance(value, dict):
            _reject_sensitive_dict(value)
