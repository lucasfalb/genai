from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncConnection

from app.object_storage import ObjectStorageError, public_object_storage
from app.rbac import Permission
from app.responses import api_success
from app.schemas import (
    ApiResponse,
    ChannelConfigResponse,
    ChannelConfigUpdateRequest,
)
from database.repositories.channel_configs import ChannelConfigRepository
from dependencies.auth import get_connection, require_permission
from database.connection import TenantContext


router = APIRouter(prefix="/tenant/instances/{instance_id}/channels", tags=["tenant-channels"])

_SUPPORTED_CHANNELS = {"widget", "api", "webhook", "whatsapp"}


def _to_response(record) -> ChannelConfigResponse:
    return ChannelConfigResponse(
        id=str(record.id),
        channel=record.channel,
        is_active=record.is_active,
        config=record.config,
        allowed_origins=record.allowed_origins,
        created_at=record.created_at.isoformat(),
    )


@router.get(
    "/{channel}",
    response_model=ApiResponse[ChannelConfigResponse],
    summary="Get channel configuration",
    description="Returns the current configuration for a channel, or defaults if not yet saved.",
    tags=["tenant-channels"],
)
async def get_channel_config(
    instance_id: UUID,
    channel: str,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
):
    if channel not in _SUPPORTED_CHANNELS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown channel: {channel}")

    record = await ChannelConfigRepository(connection).get(
        tenant_id=context.tenant_id,
        instance_id=instance_id,
        channel=channel,
    )
    if record is None:
        return api_success(
            ChannelConfigResponse(
                id="",
                channel=channel,
                is_active=False,
                config={},
                allowed_origins=[],
                created_at="",
            )
        )
    return api_success(_to_response(record))


@router.put(
    "/{channel}",
    response_model=ApiResponse[ChannelConfigResponse],
    summary="Save channel configuration",
    description="Upserts the channel configuration. Creates the record if it does not yet exist.",
    tags=["tenant-channels"],
)
async def update_channel_config(
    instance_id: UUID,
    channel: str,
    body: ChannelConfigUpdateRequest,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
):
    if channel not in _SUPPORTED_CHANNELS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown channel: {channel}")

    record = await ChannelConfigRepository(connection).upsert(
        tenant_id=context.tenant_id,
        instance_id=instance_id,
        channel=channel,
        config=body.config.model_dump(mode="json"),
        allowed_origins=body.allowed_origins,
        is_active=body.is_active,
    )
    return api_success(_to_response(record))


@router.post(
    "/{channel}/activate",
    response_model=ApiResponse[ChannelConfigResponse],
    summary="Activate a channel",
    description="Sets is_active=true for the channel, creating the config record if needed.",
    tags=["tenant-channels"],
)
async def activate_channel(
    instance_id: UUID,
    channel: str,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
):
    if channel not in _SUPPORTED_CHANNELS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown channel: {channel}")

    repo = ChannelConfigRepository(connection)
    existing = await repo.get(
        tenant_id=context.tenant_id,
        instance_id=instance_id,
        channel=channel,
    )
    record = await repo.upsert(
        tenant_id=context.tenant_id,
        instance_id=instance_id,
        channel=channel,
        config=existing.config if existing else {},
        allowed_origins=existing.allowed_origins if existing else [],
        is_active=True,
    )
    return api_success(_to_response(record))


@router.post(
    "/{channel}/deactivate",
    response_model=ApiResponse[ChannelConfigResponse],
    summary="Deactivate a channel",
    description="Sets is_active=false for the channel.",
    tags=["tenant-channels"],
)
async def deactivate_channel(
    instance_id: UUID,
    channel: str,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
):
    if channel not in _SUPPORTED_CHANNELS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown channel: {channel}")

    repo = ChannelConfigRepository(connection)
    existing = await repo.get(
        tenant_id=context.tenant_id,
        instance_id=instance_id,
        channel=channel,
    )
    record = await repo.upsert(
        tenant_id=context.tenant_id,
        instance_id=instance_id,
        channel=channel,
        config=existing.config if existing else {},
        allowed_origins=existing.allowed_origins if existing else [],
        is_active=False,
    )
    return api_success(_to_response(record))


_ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/svg+xml"}
_MAX_IMAGE_BYTES = 2 * 1024 * 1024  # 2 MB


@router.post(
    "/{channel}/upload-image",
    response_model=ApiResponse[dict],
    summary="Upload widget image asset",
    description="Uploads an image (avatar or logo) to object storage and returns the public URL.",
    tags=["tenant-channels"],
)
async def upload_channel_image(
    instance_id: UUID,
    channel: str,
    file: UploadFile = File(...),
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
):
    if channel not in _SUPPORTED_CHANNELS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown channel: {channel}")

    content_type = file.content_type or "application/octet-stream"
    if content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported image type. Allowed: PNG, JPEG, WebP, SVG.",
        )

    body = await file.read()
    if len(body) > _MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image must be under 2 MB.",
        )

    ext = content_type.split("/")[-1].replace("svg+xml", "svg")
    key = f"widget-assets/{context.tenant_id}/{instance_id}/{uuid4().hex}.{ext}"

    try:
        await public_object_storage.put_object(key=key, body=body, content_type=content_type)
    except ObjectStorageError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    url = f"{public_object_storage.endpoint_url}/{public_object_storage.bucket_name}/{key}"
    return api_success({"url": url})
