from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


@dataclass(frozen=True)
class AgentLinkRecord:
    id: UUID
    tenant_id: UUID
    source_instance_id: UUID
    target_instance_id: UUID
    target_name: str
    target_description: str | None
    transfer_tool_name: str
    trigger_description: str
    handoff_instructions: str | None
    context_policy: dict
    transfer_mode: str
    is_enabled: bool
    created_at: datetime
    updated_at: datetime | None


class AgentLinkRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def list_by_source(self, *, tenant_id: UUID, source_instance_id: UUID) -> list[AgentLinkRecord]:
        result = await self.connection.execute(
            text(
                """
                SELECT al.id,
                       al.tenant_id,
                       al.source_instance_id,
                       al.target_instance_id,
                       target.name AS target_name,
                       target.description AS target_description,
                       al.transfer_tool_name,
                       al.trigger_description,
                       al.handoff_instructions,
                       al.context_policy,
                       al.transfer_mode,
                       al.is_enabled,
                       al.created_at,
                       al.updated_at
                FROM agent_links al
                JOIN agent_instances source
                  ON source.id = al.source_instance_id
                 AND source.tenant_id = al.tenant_id
                JOIN agent_instances target
                  ON target.id = al.target_instance_id
                 AND target.tenant_id = al.tenant_id
                WHERE al.tenant_id = :tenant_id
                  AND al.source_instance_id = :source_instance_id
                ORDER BY al.created_at DESC, al.transfer_tool_name
                """
            ),
            {"tenant_id": tenant_id, "source_instance_id": source_instance_id},
        )
        return [_from_row(row) for row in result.fetchall()]

    async def get(self, *, tenant_id: UUID, source_instance_id: UUID, link_id: UUID) -> AgentLinkRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT al.id,
                       al.tenant_id,
                       al.source_instance_id,
                       al.target_instance_id,
                       target.name AS target_name,
                       target.description AS target_description,
                       al.transfer_tool_name,
                       al.trigger_description,
                       al.handoff_instructions,
                       al.context_policy,
                       al.transfer_mode,
                       al.is_enabled,
                       al.created_at,
                       al.updated_at
                FROM agent_links al
                JOIN agent_instances target
                  ON target.id = al.target_instance_id
                 AND target.tenant_id = al.tenant_id
                WHERE al.tenant_id = :tenant_id
                  AND al.source_instance_id = :source_instance_id
                  AND al.id = :link_id
                """
            ),
            {"tenant_id": tenant_id, "source_instance_id": source_instance_id, "link_id": link_id},
        )
        row = result.one_or_none()
        return _from_row(row) if row else None

    async def create(
        self,
        *,
        tenant_id: UUID,
        source_instance_id: UUID,
        target_instance_id: UUID,
        transfer_tool_name: str,
        trigger_description: str,
        handoff_instructions: str | None,
        context_policy: dict,
        transfer_mode: str,
        is_enabled: bool = True,
    ) -> AgentLinkRecord | None:
        result = await self.connection.execute(
            text(
                """
                WITH source AS (
                    SELECT id FROM agent_instances
                    WHERE id = :source_instance_id
                      AND tenant_id = :tenant_id
                      AND status <> 'archived'
                ),
                target AS (
                    SELECT id, name, description FROM agent_instances
                    WHERE id = :target_instance_id
                      AND tenant_id = :tenant_id
                      AND status <> 'archived'
                )
                INSERT INTO agent_links (
                    tenant_id,
                    source_instance_id,
                    target_instance_id,
                    transfer_tool_name,
                    trigger_description,
                    handoff_instructions,
                    context_policy,
                    transfer_mode,
                    is_enabled,
                    updated_at
                )
                SELECT :tenant_id,
                       source.id,
                       target.id,
                       :transfer_tool_name,
                       :trigger_description,
                       :handoff_instructions,
                       CAST(:context_policy AS jsonb),
                       :transfer_mode,
                       :is_enabled,
                       now()
                FROM source, target
                RETURNING id,
                          tenant_id,
                          source_instance_id,
                          target_instance_id,
                          (SELECT name FROM target) AS target_name,
                          (SELECT description FROM target) AS target_description,
                          transfer_tool_name,
                          trigger_description,
                          handoff_instructions,
                          context_policy,
                          transfer_mode,
                          is_enabled,
                          created_at,
                          updated_at
                """
            ),
            {
                "tenant_id": tenant_id,
                "source_instance_id": source_instance_id,
                "target_instance_id": target_instance_id,
                "transfer_tool_name": transfer_tool_name,
                "trigger_description": trigger_description,
                "handoff_instructions": handoff_instructions,
                "context_policy": _json_text(context_policy),
                "transfer_mode": transfer_mode,
                "is_enabled": is_enabled,
            },
        )
        row = result.one_or_none()
        return _from_row(row) if row else None

    async def update(
        self,
        *,
        tenant_id: UUID,
        source_instance_id: UUID,
        link_id: UUID,
        transfer_tool_name: str | None = None,
        trigger_description: str | None = None,
        handoff_instructions: str | None = None,
        context_policy: dict | None = None,
        transfer_mode: str | None = None,
        is_enabled: bool | None = None,
    ) -> AgentLinkRecord | None:
        result = await self.connection.execute(
            text(
                """
                UPDATE agent_links al
                SET transfer_tool_name = COALESCE(:transfer_tool_name, transfer_tool_name),
                    trigger_description = COALESCE(:trigger_description, trigger_description),
                    handoff_instructions = COALESCE(:handoff_instructions, handoff_instructions),
                    context_policy = COALESCE(CAST(:context_policy AS jsonb), context_policy),
                    transfer_mode = COALESCE(:transfer_mode, transfer_mode),
                    is_enabled = COALESCE(:is_enabled, is_enabled),
                    updated_at = now()
                FROM agent_instances target
                WHERE al.target_instance_id = target.id
                  AND target.tenant_id = al.tenant_id
                  AND al.tenant_id = :tenant_id
                  AND al.source_instance_id = :source_instance_id
                  AND al.id = :link_id
                RETURNING al.id,
                          al.tenant_id,
                          al.source_instance_id,
                          al.target_instance_id,
                          target.name AS target_name,
                          target.description AS target_description,
                          al.transfer_tool_name,
                          al.trigger_description,
                          al.handoff_instructions,
                          al.context_policy,
                          al.transfer_mode,
                          al.is_enabled,
                          al.created_at,
                          al.updated_at
                """
            ),
            {
                "tenant_id": tenant_id,
                "source_instance_id": source_instance_id,
                "link_id": link_id,
                "transfer_tool_name": transfer_tool_name,
                "trigger_description": trigger_description,
                "handoff_instructions": handoff_instructions,
                "context_policy": _json_text(context_policy) if context_policy is not None else None,
                "transfer_mode": transfer_mode,
                "is_enabled": is_enabled,
            },
        )
        row = result.one_or_none()
        return _from_row(row) if row else None

    async def set_enabled(
        self,
        *,
        tenant_id: UUID,
        source_instance_id: UUID,
        link_id: UUID,
        is_enabled: bool,
    ) -> AgentLinkRecord | None:
        return await self.update(
            tenant_id=tenant_id,
            source_instance_id=source_instance_id,
            link_id=link_id,
            is_enabled=is_enabled,
        )

    async def delete(self, *, tenant_id: UUID, source_instance_id: UUID, link_id: UUID) -> AgentLinkRecord | None:
        existing = await self.get(tenant_id=tenant_id, source_instance_id=source_instance_id, link_id=link_id)
        if existing is None:
            return None
        await self.connection.execute(
            text(
                """
                DELETE FROM agent_links
                WHERE tenant_id = :tenant_id
                  AND source_instance_id = :source_instance_id
                  AND id = :link_id
                """
            ),
            {"tenant_id": tenant_id, "source_instance_id": source_instance_id, "link_id": link_id},
        )
        return existing


def _from_row(row) -> AgentLinkRecord:
    return AgentLinkRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        source_instance_id=row.source_instance_id,
        target_instance_id=row.target_instance_id,
        target_name=row.target_name,
        target_description=row.target_description,
        transfer_tool_name=row.transfer_tool_name,
        trigger_description=row.trigger_description,
        handoff_instructions=row.handoff_instructions,
        context_policy=row.context_policy or {},
        transfer_mode=row.transfer_mode,
        is_enabled=row.is_enabled,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _json_text(value: dict) -> str:
    import json

    return json.dumps(value or {})
