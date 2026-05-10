import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncConnection

from app.rbac import Permission
from app.responses import api_success
from app.schemas import (
    ApiResponse,
    MessageResponse,
    ProviderConfigRequest,
    ProviderModelInfo,
    ProviderModelsResponse,
    ProviderInfo,
    TenantProvidersResponse,
)
from app.workflow_audit import record_tenant_mutation
from database.connection import TenantContext
from database.repositories.ai_configs import AIConfigRepository
from dependencies.auth import get_connection, require_permission
from engine.ai_provider import decrypt_api_key, encrypt_api_key

router = APIRouter(prefix="/tenant/settings", tags=["tenant-settings"])


@router.get(
    "",
    response_model=ApiResponse[TenantProvidersResponse],
    summary="Get tenant providers configuration",
    description="Returns all configured AI providers for this tenant. API keys are never exposed.",
)
async def get_tenant_providers(
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[TenantProvidersResponse]:
    record = await AIConfigRepository(connection).get_tenant_providers(tenant_id=context.tenant_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")

    response = TenantProvidersResponse(
        tenant_id=str(record.tenant_id),
        providers=[
            ProviderInfo(
                name=p.name,
                enabled=p.enabled,
                has_api_key=p.has_api_key,
                api_key_hint=p.api_key_hint,
                configured_at=p.configured_at,
                configured_by=p.configured_by,
            )
            for p in record.providers
        ],
    )
    return api_success(response)


@router.post(
    "",
    response_model=ApiResponse[TenantProvidersResponse],
    summary="Add or update provider configuration",
    description="Adds or updates a provider configuration. Send api_key to save a new key, or enabled to toggle the provider on/off.",
)
async def upsert_provider(
    payload: ProviderConfigRequest,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[TenantProvidersResponse]:
    if payload.api_key is not None:
        encrypted = encrypt_api_key(payload.api_key)
        hint = payload.api_key[:12] + "..."
        record = await AIConfigRepository(connection).upsert_provider(
            tenant_id=context.tenant_id,
            configured_by=context.user_id,
            provider_name=payload.name,
            api_key_encrypted=encrypted,
            api_key_hint=hint,
        )
    elif payload.enabled is not None:
        record = await AIConfigRepository(connection).upsert_provider(
            tenant_id=context.tenant_id,
            configured_by=context.user_id,
            provider_name=payload.name,
            enabled=payload.enabled,
        )
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Either api_key or enabled must be provided.")

    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")

    response = TenantProvidersResponse(
        tenant_id=str(record.tenant_id),
        providers=[
            ProviderInfo(
                name=p.name,
                enabled=p.enabled,
                has_api_key=p.has_api_key,
                api_key_hint=p.api_key_hint,
                configured_at=p.configured_at,
                configured_by=p.configured_by,
            )
            for p in record.providers
        ],
    )

    action = "tenant_provider.toggled" if payload.api_key is None else "tenant_provider.configured"
    await record_tenant_mutation(
        connection=connection,
        context=context,
        action=action,
        resource="tenant_providers",
        resource_id=str(context.tenant_id),
        snapshot=response.model_dump(mode="json"),
        metadata={"provider_name": payload.name},
    )
    msg = f"Provider {payload.name} toggled." if payload.api_key is None else f"Provider {payload.name} configured successfully."
    return api_success(response, message=msg)


@router.delete(
    "",
    response_model=ApiResponse[MessageResponse],
    summary="Delete provider configuration",
    description="Removes a provider configuration from this tenant.",
)
async def delete_provider(
    provider_name: str = Query(..., description="Name of the provider to delete"),
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[MessageResponse]:
    record = await AIConfigRepository(connection).delete_provider(
        tenant_id=context.tenant_id,
        provider_name=provider_name,
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Provider not found")

    await record_tenant_mutation(
        connection=connection,
        context=context,
        action="tenant_provider.deleted",
        resource="tenant_providers",
        resource_id=str(context.tenant_id),
        snapshot=None,
        metadata={"provider_name": provider_name},
    )
    message = f"Provider {provider_name} removed."
    return api_success(MessageResponse(message=message), message=message)


@router.get(
    "/{provider}/models",
    response_model=ApiResponse[ProviderModelsResponse],
    summary="List available models for a provider",
    description="Fetches available models from the provider API using the tenant's stored API key.",
)
async def get_provider_models(
    provider: str,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[ProviderModelsResponse]:
    encrypted = await AIConfigRepository(connection).get_provider_encrypted_key(
        tenant_id=context.tenant_id,
        provider_name=provider,
    )
    if not encrypted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Provider '{provider}' not configured for this tenant")

    api_key = decrypt_api_key(encrypted)
    models = await _fetch_provider_models(provider, api_key)

    return api_success(ProviderModelsResponse(provider=provider, models=[ProviderModelInfo(id=m) for m in models]))


async def _fetch_provider_models(provider: str, api_key: str) -> list[str]:
    if provider == "openai":
        return await _fetch_openai_models(api_key)
    elif provider == "anthropic":
        return await _fetch_anthropic_models(api_key)
    elif provider == "google":
        return await _fetch_gemini_models(api_key)
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown provider: {provider}")


async def _fetch_openai_models(api_key: str) -> list[str]:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        resp.raise_for_status()
        data = resp.json()
        return [m["id"] for m in data.get("data", []) if not m["id"].startswith("ft:")]


async def _fetch_anthropic_models(api_key: str) -> list[str]:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://api.anthropic.com/v1/models",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return [m["id"] for m in data.get("data", [])]


async def _fetch_gemini_models(api_key: str) -> list[str]:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"key": api_key},
        )
        resp.raise_for_status()
        data = resp.json()
        return [m["name"].replace("models/", "") for m in data.get("models", [])]
