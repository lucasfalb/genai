from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.rbac import Permission
from app.registry_cache import ToolMetadataCache
from app.responses import api_success
from app.schemas import (
    ActivationRequest,
    ApiResponse,
    CatalogSkillResponse,
    CatalogToolResponse,
    CredentialRequest,
    CredentialResponse,
    RegistryCatalogResponse,
    SkillActivationResponse,
    ToolActivationResponse,
    ToolMetadataResponse,
)
from database.connection import TenantContext, tenant_connection
from database.repositories.registry import (
    CredentialRecord,
    RegistryRepository,
    SkillActivationRecord,
    ToolActivationRecord,
)
from dependencies.auth import require_permission
from engine.prompt_cache import PromptCache


router = APIRouter(prefix="/registry", tags=["tenant-registry"])
SENSITIVE_METADATA_KEYS = {"token", "api_key", "apikey", "password", "secret", "authorization", "auth_header"}


@router.get(
    "/catalog",
    response_model=ApiResponse[RegistryCatalogResponse],
    summary="Get registry catalog",
    description="Returns the catalog of all globally active skills and tools available for activation on agent instances. Excludes platform-internal fields like prompt blocks, schemas and executors.",
)
async def get_registry_catalog(
    context: TenantContext = Depends(require_permission(Permission.MANAGE_SKILLS_TOOLS)),
) -> ApiResponse[RegistryCatalogResponse]:
    async with tenant_connection(context) as connection:
        repository = RegistryRepository(connection)
        skills = [
            CatalogSkillResponse(
                slug=s.slug,
                name=s.name,
                description=s.description,
                category=s.category,
                requires_credential=s.requires_credential,
            )
            for s in await repository.list_skills()
            if s.is_active
        ]
        tools = [
            CatalogToolResponse(
                slug=t.slug,
                name=t.name,
                description=t.description,
                category=t.category,
            )
            for t in await repository.list_tools()
        ]
        return api_success(RegistryCatalogResponse(skills=skills, tools=tools))


@router.get(
    "/instances/{instance_id}/metadata",
    response_model=ApiResponse[ToolMetadataResponse],
    summary="Get instance registry metadata",
    description="Returns active skills and tools for one agent instance in the selected tenant. The response excludes credentials and secret references.",
)
async def get_instance_metadata(
    instance_id: UUID,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_SKILLS_TOOLS)),
) -> ApiResponse[ToolMetadataResponse]:
    async with tenant_connection(context) as connection:
        metadata = await ToolMetadataCache(connection).get(tenant_id=context.tenant_id, instance_id=instance_id)
        return api_success(metadata)


@router.put(
    "/instances/{instance_id}/skills/{skill_slug}",
    response_model=ApiResponse[SkillActivationResponse],
    summary="Configure instance skill",
    description="Enables or disables one active global skill for an agent instance in the selected tenant and invalidates registry metadata and prompt caches.",
)
async def configure_instance_skill(
    instance_id: UUID,
    skill_slug: str,
    payload: ActivationRequest,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_SKILLS_TOOLS)),
) -> ApiResponse[SkillActivationResponse]:
    async with tenant_connection(context) as connection:
        repository = RegistryRepository(connection)
        activation = await repository.activate_skill(
            tenant_id=context.tenant_id,
            instance_id=instance_id,
            skill_slug=skill_slug,
            is_enabled=payload.is_enabled,
            config=payload.config,
        )
        if activation is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Instance or skill not found")
        await _invalidate_instance_caches(connection, tenant_id=context.tenant_id, instance_id=instance_id)
        return api_success(_skill_activation_response(activation), message="Skill configuration updated.")


@router.put(
    "/instances/{instance_id}/tools/{tool_slug}",
    response_model=ApiResponse[ToolActivationResponse],
    summary="Configure instance tool",
    description="Enables or disables one global utility tool for an agent instance in the selected tenant and invalidates registry metadata and prompt caches.",
)
async def configure_instance_tool(
    instance_id: UUID,
    tool_slug: str,
    payload: ActivationRequest,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_SKILLS_TOOLS)),
) -> ApiResponse[ToolActivationResponse]:
    async with tenant_connection(context) as connection:
        repository = RegistryRepository(connection)
        activation = await repository.activate_tool(
            tenant_id=context.tenant_id,
            instance_id=instance_id,
            tool_slug=tool_slug,
            is_enabled=payload.is_enabled,
            config=payload.config,
        )
        if activation is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Instance or tool not found")
        await _invalidate_instance_caches(connection, tenant_id=context.tenant_id, instance_id=instance_id)
        return api_success(_tool_activation_response(activation), message="Tool configuration updated.")


@router.get(
    "/credentials",
    response_model=ApiResponse[list[CredentialResponse]],
    summary="List tenant credential references",
    description="Lists credential references configured for the selected tenant. Secret values are never returned by this endpoint.",
)
async def list_credential_refs(
    context: TenantContext = Depends(require_permission(Permission.MANAGE_SKILLS_TOOLS)),
) -> ApiResponse[list[CredentialResponse]]:
    async with tenant_connection(context) as connection:
        repository = RegistryRepository(connection)
        return api_success(
            [_credential_response(item) for item in await repository.list_credentials(tenant_id=context.tenant_id)]
        )


@router.put(
    "/credentials/{skill_slug}",
    response_model=ApiResponse[CredentialResponse],
    summary="Configure tenant credential reference",
    description="Stores or updates a non-secret vault reference for a credential required by a skill in the selected tenant.",
)
async def configure_credential_ref(
    skill_slug: str,
    payload: CredentialRequest,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_SKILLS_TOOLS)),
) -> ApiResponse[CredentialResponse]:
    _reject_sensitive_metadata(payload.metadata)
    async with tenant_connection(context) as connection:
        repository = RegistryRepository(connection)
        credential = await repository.upsert_credential(
            tenant_id=context.tenant_id,
            skill_slug=skill_slug,
            secret_ref=payload.secret_ref,
            metadata=payload.metadata,
        )
        if credential is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Credential-enabled skill not found")
        return api_success(_credential_response(credential), message="Credential reference updated.")


def _reject_sensitive_metadata(metadata: dict) -> None:
    for key, value in metadata.items():
        normalized = key.lower().replace("-", "_")
        if normalized in SENSITIVE_METADATA_KEYS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Sensitive credential metadata is not allowed: {key}")
        if isinstance(value, dict):
            _reject_sensitive_metadata(value)


async def _invalidate_instance_caches(connection, *, tenant_id: UUID, instance_id: UUID) -> None:
    await ToolMetadataCache(connection).invalidate(tenant_id=tenant_id, instance_id=instance_id)
    await PromptCache(connection).invalidate(tenant_id=tenant_id, instance_id=instance_id)


def _skill_activation_response(record: SkillActivationRecord) -> SkillActivationResponse:
    return SkillActivationResponse(**record.__dict__)


def _tool_activation_response(record: ToolActivationRecord) -> ToolActivationResponse:
    return ToolActivationResponse(**record.__dict__)


def _credential_response(record: CredentialRecord) -> CredentialResponse:
    return CredentialResponse(**record.__dict__)
