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
