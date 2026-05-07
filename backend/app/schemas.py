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


class TenantMemberUpdateRequest(BaseModel):
    role: str | None = Field(default=None, pattern=r"^(tenant_admin|member|viewer)$")
    status: str | None = Field(default=None, pattern=r"^(active|pending|suspended)$")


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


class ToolDefinitionResponse(ToolDefinitionRequest):
    id: UUID


class ActivationRequest(BaseModel):
    is_enabled: bool = True
    config: dict = Field(default_factory=dict)


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
    config: dict


class ToolMetadataResponse(BaseModel):
    tenant_id: UUID
    instance_id: UUID
    skills: list[RegistrySkillMetadata]
    tools: list[RegistryToolMetadata]


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


class TenantAIConfigRequest(BaseModel):
    provider: str = Field(default="openai", pattern=r"^[a-z0-9_-]+$", max_length=80)
    api_key: str = Field(min_length=1, max_length=512)
    default_model: str | None = Field(default=None, max_length=120)
    enabled: bool = True


class TenantAIConfigResponse(BaseModel):
    tenant_id: UUID
    provider: str | None
    default_model: str | None
    enabled: bool
    has_api_key: bool
    configured_by: UUID | None


class AgentInstanceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    core_prompt: str = Field(min_length=1)
    model: str = Field(default="gpt-4.1-mini", max_length=120)
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
    title: str = Field(min_length=1, max_length=160)
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


class AgentPromptConfigRequest(BaseModel):
    instruction_blocks: list[AgentInstructionBlock] = Field(default_factory=list, max_length=50)
    guardrails: list[AgentGuardrail] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def reject_duplicate_ids(self):
        instruction_ids = [item.id for item in self.instruction_blocks]
        guardrail_ids = [item.id for item in self.guardrails]
        if len(instruction_ids) != len(set(instruction_ids)):
            raise ValueError("Duplicate instruction block ids are not allowed")
        if len(guardrail_ids) != len(set(guardrail_ids)):
            raise ValueError("Duplicate guardrail ids are not allowed")
        return self


class AgentPromptConfigResponse(BaseModel):
    tenant_id: UUID
    instance_id: UUID
    instruction_blocks: list[AgentInstructionBlock]
    guardrails: list[AgentGuardrail]


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
