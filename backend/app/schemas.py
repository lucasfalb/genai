from datetime import datetime
from typing import Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

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


class PlatformAIConfigRequest(BaseModel):
    provider: str = Field(default="openai", pattern=r"^[a-z0-9_-]+$", max_length=80)
    api_key: str = Field(min_length=1, max_length=512)
    default_model: str = Field(default="gpt-4.1-mini", max_length=120)
    base_url: str | None = Field(default=None, max_length=512)


class PlatformAIConfigResponse(BaseModel):
    id: UUID
    provider: str
    default_model: str
    base_url: str | None
    is_active: bool
    api_key_hint: str = "****"


class TenantAIConfigRequest(BaseModel):
    provider: str = Field(default="openai", pattern=r"^[a-z0-9_-]+$", max_length=80)
    api_key: str = Field(min_length=1, max_length=512)
    default_model: str | None = Field(default=None, max_length=120)
    base_url: str | None = Field(default=None, max_length=512)


class TenantAIConfigResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    provider: str
    default_model: str | None
    base_url: str | None
    is_active: bool
    api_key_hint: str = "****"


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
