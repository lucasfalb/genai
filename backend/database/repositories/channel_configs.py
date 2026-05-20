import json
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


@dataclass(frozen=True)
class ChannelConfigRecord:
    id: UUID
    tenant_id: UUID
    instance_id: UUID
    channel: str
    config: dict
    allowed_origins: list[str]
    is_active: bool
    created_at: datetime


class ChannelConfigRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def _set_tenant(self, tenant_id: UUID) -> None:
        await self.connection.execute(
            text("SELECT set_config('app.current_tenant_id', :tid, true)"),
            {"tid": str(tenant_id)},
        )

    async def get(self, *, tenant_id: UUID, instance_id: UUID, channel: str) -> ChannelConfigRecord | None:
        await self._set_tenant(tenant_id)
        result = await self.connection.execute(
            text(
                """
                SELECT id, tenant_id, instance_id, channel, config, allowed_origins, is_active, created_at
                FROM agent_channel_configs
                WHERE tenant_id = :tenant_id
                  AND instance_id = :instance_id
                  AND channel = :channel
                """
            ),
            {"tenant_id": tenant_id, "instance_id": instance_id, "channel": channel},
        )
        row = result.fetchone()
        return _from_row(row) if row else None

    async def upsert(
        self,
        *,
        tenant_id: UUID,
        instance_id: UUID,
        channel: str,
        config: dict,
        allowed_origins: list[str],
        is_active: bool | None = None,
    ) -> ChannelConfigRecord:
        await self._set_tenant(tenant_id)
        params: dict = {
            "tenant_id": tenant_id,
            "instance_id": instance_id,
            "channel": channel,
            "config": json.dumps(config),
            "allowed_origins": allowed_origins,
        }

        if is_active is None:
            result = await self.connection.execute(
                text(
                    """
                    INSERT INTO agent_channel_configs
                        (tenant_id, instance_id, channel, config, allowed_origins)
                    VALUES (:tenant_id, :instance_id, :channel, CAST(:config AS JSONB), :allowed_origins)
                    ON CONFLICT (tenant_id, instance_id, channel)
                    DO UPDATE SET
                        config = EXCLUDED.config,
                        allowed_origins = EXCLUDED.allowed_origins
                    RETURNING id, tenant_id, instance_id, channel, config, allowed_origins, is_active, created_at
                    """
                ),
                params,
            )
        else:
            params["is_active"] = is_active
            result = await self.connection.execute(
                text(
                    """
                    INSERT INTO agent_channel_configs
                        (tenant_id, instance_id, channel, config, allowed_origins, is_active)
                    VALUES (:tenant_id, :instance_id, :channel, CAST(:config AS JSONB), :allowed_origins, :is_active)
                    ON CONFLICT (tenant_id, instance_id, channel)
                    DO UPDATE SET
                        config = EXCLUDED.config,
                        allowed_origins = EXCLUDED.allowed_origins,
                        is_active = EXCLUDED.is_active
                    RETURNING id, tenant_id, instance_id, channel, config, allowed_origins, is_active, created_at
                    """
                ),
                params,
            )

        row = result.fetchone()
        return _from_row(row)


def _from_row(row) -> ChannelConfigRecord:
    raw_config = row.config
    if isinstance(raw_config, str):
        raw_config = json.loads(raw_config)
    return ChannelConfigRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        instance_id=row.instance_id,
        channel=row.channel,
        config=raw_config or {},
        allowed_origins=list(row.allowed_origins or []),
        is_active=bool(row.is_active),
        created_at=row.created_at,
    )
