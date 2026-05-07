import json
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


@dataclass(frozen=True)
class AgentInstanceRecord:
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


@dataclass(frozen=True)
class AgentPromptConfigRecord:
    tenant_id: UUID
    instance_id: UUID
    instruction_blocks: list
    guardrails: list


class AgentInstanceRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def list_instances(self, *, tenant_id: UUID) -> list[AgentInstanceRecord]:
        result = await self.connection.execute(
            text(
                """
                SELECT id, tenant_id, name, description, core_prompt, model, temperature, status, rag_scope, created_by
                FROM agent_instances
                WHERE tenant_id = :tenant_id
                ORDER BY created_at DESC
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [_from_row(row) for row in result.fetchall()]

    async def get_instance(self, *, tenant_id: UUID, instance_id: UUID) -> AgentInstanceRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT id, tenant_id, name, description, core_prompt, model, temperature, status, rag_scope, created_by
                FROM agent_instances
                WHERE tenant_id = :tenant_id AND id = :instance_id
                """
            ),
            {"tenant_id": tenant_id, "instance_id": instance_id},
        )
        row = result.one_or_none()
        return _from_row(row) if row else None

    async def create_instance(
        self,
        *,
        tenant_id: UUID,
        name: str,
        core_prompt: str,
        created_by: UUID,
        description: str | None = None,
        model: str = "gpt-4.1-mini",
        temperature: float = 0.2,
        rag_scope: list | None = None,
    ) -> AgentInstanceRecord:
        result = await self.connection.execute(
            text(
                """
                INSERT INTO agent_instances
                  (tenant_id, name, description, core_prompt, model, temperature, rag_scope, created_by, status)
                VALUES
                  (:tenant_id, :name, :description, :core_prompt, :model, :temperature,
                   CAST(:rag_scope AS jsonb), :created_by, 'inactive')
                RETURNING id, tenant_id, name, description, core_prompt, model, temperature, status, rag_scope, created_by
                """
            ),
            {
                "tenant_id": tenant_id,
                "name": name,
                "description": description,
                "core_prompt": core_prompt,
                "model": model,
                "temperature": temperature,
                "rag_scope": json.dumps(rag_scope or []),
                "created_by": created_by,
            },
        )
        return _from_row(result.one())

    async def update_instance(
        self,
        *,
        tenant_id: UUID,
        instance_id: UUID,
        name: str | None = None,
        description: str | None = None,
        core_prompt: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        status: str | None = None,
        rag_scope: list | None = None,
    ) -> AgentInstanceRecord | None:
        result = await self.connection.execute(
            text(
                """
                UPDATE agent_instances
                SET
                  name        = COALESCE(:name, name),
                  description = COALESCE(:description, description),
                  core_prompt = COALESCE(:core_prompt, core_prompt),
                  model       = COALESCE(:model, model),
                  temperature = COALESCE(:temperature, temperature),
                  status      = COALESCE(:status, status),
                  rag_scope   = COALESCE(CAST(:rag_scope AS jsonb), rag_scope),
                  updated_at  = now()
                WHERE tenant_id = :tenant_id AND id = :instance_id
                RETURNING id, tenant_id, name, description, core_prompt, model, temperature, status, rag_scope, created_by
                """
            ),
            {
                "tenant_id": tenant_id,
                "instance_id": instance_id,
                "name": name,
                "description": description,
                "core_prompt": core_prompt,
                "model": model,
                "temperature": temperature,
                "status": status,
                "rag_scope": json.dumps(rag_scope) if rag_scope is not None else None,
            },
        )
        row = result.one_or_none()
        return _from_row(row) if row else None

    async def archive_instance(self, *, tenant_id: UUID, instance_id: UUID) -> AgentInstanceRecord | None:
        result = await self.connection.execute(
            text(
                """
                UPDATE agent_instances
                SET status = 'archived', updated_at = now()
                WHERE tenant_id = :tenant_id AND id = :instance_id
                RETURNING id, tenant_id, name, description, core_prompt, model, temperature, status, rag_scope, created_by
                """
            ),
            {"tenant_id": tenant_id, "instance_id": instance_id},
        )
        row = result.one_or_none()
        return _from_row(row) if row else None

    async def get_prompt_config(self, *, tenant_id: UUID, instance_id: UUID) -> AgentPromptConfigRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT tenant_id, id AS instance_id, instruction_blocks, guardrails
                FROM agent_instances
                WHERE tenant_id = :tenant_id AND id = :instance_id
                """
            ),
            {"tenant_id": tenant_id, "instance_id": instance_id},
        )
        row = result.one_or_none()
        return _prompt_config_from_row(row) if row else None

    async def update_prompt_config(
        self,
        *,
        tenant_id: UUID,
        instance_id: UUID,
        instruction_blocks: list,
        guardrails: list,
    ) -> AgentPromptConfigRecord | None:
        result = await self.connection.execute(
            text(
                """
                UPDATE agent_instances
                SET instruction_blocks = CAST(:instruction_blocks AS jsonb),
                    guardrails = CAST(:guardrails AS jsonb),
                    updated_at = now()
                WHERE tenant_id = :tenant_id AND id = :instance_id
                RETURNING tenant_id, id AS instance_id, instruction_blocks, guardrails
                """
            ),
            {
                "tenant_id": tenant_id,
                "instance_id": instance_id,
                "instruction_blocks": json.dumps(instruction_blocks),
                "guardrails": json.dumps(guardrails),
            },
        )
        row = result.one_or_none()
        return _prompt_config_from_row(row) if row else None


def _from_row(row) -> AgentInstanceRecord:
    return AgentInstanceRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        name=row.name,
        description=row.description,
        core_prompt=row.core_prompt,
        model=row.model,
        temperature=row.temperature,
        status=row.status,
        rag_scope=row.rag_scope or [],
        created_by=row.created_by,
    )


def _prompt_config_from_row(row) -> AgentPromptConfigRecord:
    return AgentPromptConfigRecord(
        tenant_id=row.tenant_id,
        instance_id=row.instance_id,
        instruction_blocks=row.instruction_blocks or [],
        guardrails=row.guardrails or [],
    )
