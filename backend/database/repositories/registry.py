import json
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


@dataclass(frozen=True)
class SkillDefinitionRecord:
    id: UUID
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
    credential_schema: dict | None
    is_active: bool


@dataclass(frozen=True)
class ToolDefinitionRecord:
    id: UUID
    slug: str
    name: str
    description: str | None
    category: str | None
    prompt_block: str
    schema: dict
    executor: str
    is_builtin: bool
    method: str
    endpoint: str | None
    headers_template: dict
    body_template: str | None
    variables_schema: list


@dataclass(frozen=True)
class SkillActivationRecord:
    id: UUID
    tenant_id: UUID
    instance_id: UUID
    skill_id: UUID
    skill_slug: str
    is_enabled: bool
    config: dict


@dataclass(frozen=True)
class ToolActivationRecord:
    id: UUID
    tenant_id: UUID
    instance_id: UUID
    tool_id: UUID
    tool_slug: str
    is_enabled: bool
    config: dict


@dataclass(frozen=True)
class CredentialRecord:
    id: UUID
    tenant_id: UUID
    skill_id: UUID
    skill_slug: str
    secret_ref: str
    metadata: dict


class RegistryRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def list_skills(self) -> list[SkillDefinitionRecord]:
        result = await self.connection.execute(
            text(
                """
                SELECT id, slug, name, description, category, prompt_block, tool_schema,
                       executor, input_schema, output_schema, requires_credential,
                       credential_schema, is_active
                FROM skill_definitions
                ORDER BY slug
                """
            )
        )
        return [_skill_definition(row) for row in result.fetchall()]

    async def upsert_skill(self, **payload) -> SkillDefinitionRecord:
        result = await self.connection.execute(
            text(
                """
                INSERT INTO skill_definitions
                  (slug, name, description, category, prompt_block, tool_schema, executor,
                   input_schema, output_schema, requires_credential, credential_schema, is_active)
                VALUES
                  (:slug, :name, :description, :category, :prompt_block, CAST(:tool_schema AS jsonb),
                   :executor, CAST(:input_schema AS jsonb), CAST(:output_schema AS jsonb),
                   :requires_credential, CAST(:credential_schema AS jsonb), :is_active)
                ON CONFLICT (slug) DO UPDATE SET
                  name = EXCLUDED.name,
                  description = EXCLUDED.description,
                  category = EXCLUDED.category,
                  prompt_block = EXCLUDED.prompt_block,
                  tool_schema = EXCLUDED.tool_schema,
                  executor = EXCLUDED.executor,
                  input_schema = EXCLUDED.input_schema,
                  output_schema = EXCLUDED.output_schema,
                  requires_credential = EXCLUDED.requires_credential,
                  credential_schema = EXCLUDED.credential_schema,
                  is_active = EXCLUDED.is_active
                RETURNING id, slug, name, description, category, prompt_block, tool_schema,
                          executor, input_schema, output_schema, requires_credential,
                          credential_schema, is_active
                """
            ),
            {
                **payload,
                "tool_schema": json.dumps(payload["tool_schema"]),
                "input_schema": json.dumps(payload["input_schema"]),
                "output_schema": json.dumps(payload["output_schema"]),
                "credential_schema": json.dumps(payload["credential_schema"]),
            },
        )
        return _skill_definition(result.one())

    async def list_tools(self) -> list[ToolDefinitionRecord]:
        result = await self.connection.execute(
            text(
                """
                SELECT id, slug, name, description, category, prompt_block, schema, executor,
                       is_builtin, method, endpoint, headers_template, body_template, variables_schema
                FROM tool_definitions
                ORDER BY slug
                """
            )
        )
        return [_tool_definition(row) for row in result.fetchall()]

    async def upsert_tool(self, **payload) -> ToolDefinitionRecord:
        result = await self.connection.execute(
            text(
                """
                INSERT INTO tool_definitions
                  (slug, name, description, category, prompt_block, schema, executor, is_builtin,
                   method, endpoint, headers_template, body_template, variables_schema)
                VALUES
                  (:slug, :name, :description, :category, :prompt_block,
                   CAST(:schema AS jsonb), :executor, :is_builtin,
                   :method, :endpoint, CAST(:headers_template AS jsonb),
                   :body_template, CAST(:variables_schema AS jsonb))
                ON CONFLICT (slug) DO UPDATE SET
                  name = EXCLUDED.name,
                  description = EXCLUDED.description,
                  category = EXCLUDED.category,
                  prompt_block = EXCLUDED.prompt_block,
                  schema = EXCLUDED.schema,
                  executor = EXCLUDED.executor,
                  is_builtin = EXCLUDED.is_builtin,
                  method = EXCLUDED.method,
                  endpoint = EXCLUDED.endpoint,
                  headers_template = EXCLUDED.headers_template,
                  body_template = EXCLUDED.body_template,
                  variables_schema = EXCLUDED.variables_schema
                RETURNING id, slug, name, description, category, prompt_block, schema, executor,
                          is_builtin, method, endpoint, headers_template, body_template, variables_schema
                """
            ),
            {
                **payload,
                "schema": json.dumps(payload["schema"]),
                "headers_template": json.dumps(payload.get("headers_template") or {}),
                "variables_schema": json.dumps(payload.get("variables_schema") or []),
            },
        )
        return _tool_definition(result.one())

    async def activate_skill(
        self,
        *,
        tenant_id: UUID,
        instance_id: UUID,
        skill_slug: str,
        is_enabled: bool,
        config: dict,
    ) -> SkillActivationRecord | None:
        result = await self.connection.execute(
            text(
                """
                WITH instance AS (
                    SELECT id FROM agent_instances
                    WHERE id = :instance_id AND tenant_id = :tenant_id
                ),
                skill AS (
                    SELECT id, slug FROM skill_definitions
                    WHERE slug = :skill_slug AND is_active = true
                )
                INSERT INTO agent_instance_skills (tenant_id, instance_id, skill_id, is_enabled, config)
                SELECT :tenant_id, instance.id, skill.id, :is_enabled, CAST(:config AS jsonb)
                FROM instance, skill
                ON CONFLICT (instance_id, skill_id) DO UPDATE SET
                  is_enabled = EXCLUDED.is_enabled,
                  config = EXCLUDED.config
                RETURNING id, tenant_id, instance_id, skill_id,
                          (SELECT slug FROM skill) AS slug, is_enabled, config
                """
            ),
            {
                "tenant_id": tenant_id,
                "instance_id": instance_id,
                "skill_slug": skill_slug,
                "is_enabled": is_enabled,
                "config": json.dumps(config),
            },
        )
        row = result.one_or_none()
        return None if row is None else _skill_activation(row)

    async def activate_tool(
        self,
        *,
        tenant_id: UUID,
        instance_id: UUID,
        tool_slug: str,
        is_enabled: bool,
        config: dict,
    ) -> ToolActivationRecord | None:
        result = await self.connection.execute(
            text(
                """
                WITH instance AS (
                    SELECT id FROM agent_instances
                    WHERE id = :instance_id AND tenant_id = :tenant_id
                ),
                tool AS (
                    SELECT id, slug FROM tool_definitions
                    WHERE slug = :tool_slug
                )
                INSERT INTO agent_instance_tools (tenant_id, instance_id, tool_id, is_enabled, config)
                SELECT :tenant_id, instance.id, tool.id, :is_enabled, CAST(:config AS jsonb)
                FROM instance, tool
                ON CONFLICT (instance_id, tool_id) DO UPDATE SET
                  is_enabled = EXCLUDED.is_enabled,
                  config = EXCLUDED.config
                RETURNING id, tenant_id, instance_id, tool_id,
                          (SELECT slug FROM tool) AS slug, is_enabled, config
                """
            ),
            {
                "tenant_id": tenant_id,
                "instance_id": instance_id,
                "tool_slug": tool_slug,
                "is_enabled": is_enabled,
                "config": json.dumps(config),
            },
        )
        row = result.one_or_none()
        return None if row is None else _tool_activation(row)

    async def upsert_credential(
        self,
        *,
        tenant_id: UUID,
        skill_slug: str,
        secret_ref: str,
        metadata: dict,
    ) -> CredentialRecord | None:
        credential_data = {"secret_ref": secret_ref, "metadata": metadata}
        result = await self.connection.execute(
            text(
                """
                WITH skill AS (
                    SELECT id, slug FROM skill_definitions
                    WHERE slug = :skill_slug AND requires_credential = true AND is_active = true
                )
                INSERT INTO tool_credentials (tenant_id, skill_id, credential_data)
                SELECT :tenant_id, skill.id, CAST(:credential_data AS jsonb)
                FROM skill
                ON CONFLICT (tenant_id, skill_id) DO UPDATE SET
                  credential_data = EXCLUDED.credential_data
                RETURNING id, tenant_id, skill_id, (SELECT slug FROM skill) AS slug, credential_data
                """
            ),
            {"tenant_id": tenant_id, "skill_slug": skill_slug, "credential_data": json.dumps(credential_data)},
        )
        row = result.one_or_none()
        return None if row is None else _credential(row)

    async def deactivate_skill(
        self, *, tenant_id: UUID, instance_id: UUID, skill_slug: str
    ) -> bool:
        result = await self.connection.execute(
            text(
                """
                DELETE FROM agent_instance_skills
                WHERE tenant_id = :tenant_id
                  AND instance_id = :instance_id
                  AND skill_id = (SELECT id FROM skill_definitions WHERE slug = :slug)
                RETURNING id
                """
            ),
            {"tenant_id": tenant_id, "instance_id": instance_id, "slug": skill_slug},
        )
        return result.one_or_none() is not None

    async def deactivate_tool(
        self, *, tenant_id: UUID, instance_id: UUID, tool_slug: str
    ) -> bool:
        result = await self.connection.execute(
            text(
                """
                DELETE FROM agent_instance_tools
                WHERE tenant_id = :tenant_id
                  AND instance_id = :instance_id
                  AND tool_id = (SELECT id FROM tool_definitions WHERE slug = :slug)
                RETURNING id
                """
            ),
            {"tenant_id": tenant_id, "instance_id": instance_id, "slug": tool_slug},
        )
        return result.one_or_none() is not None

    async def delete_skill(self, *, slug: str) -> bool:
        result = await self.connection.execute(
            text("DELETE FROM skill_definitions WHERE slug = :slug RETURNING id"),
            {"slug": slug},
        )
        return result.one_or_none() is not None

    async def delete_tool(self, *, slug: str) -> bool:
        result = await self.connection.execute(
            text("DELETE FROM tool_definitions WHERE slug = :slug RETURNING id"),
            {"slug": slug},
        )
        return result.one_or_none() is not None

    async def list_credentials(self, *, tenant_id: UUID) -> list[CredentialRecord]:
        result = await self.connection.execute(
            text(
                """
                SELECT tc.id, tc.tenant_id, tc.skill_id, sd.slug, tc.credential_data
                FROM tool_credentials tc
                JOIN skill_definitions sd ON sd.id = tc.skill_id
                WHERE tc.tenant_id = :tenant_id
                ORDER BY sd.slug
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [_credential(row) for row in result.fetchall()]

    async def load_metadata(self, *, tenant_id: UUID, instance_id: UUID) -> dict:
        skills = await self.connection.execute(
            text(
                """
                SELECT sd.slug, sd.name, sd.description, sd.category, sd.prompt_block,
                       sd.tool_schema, sd.executor, sd.input_schema, sd.output_schema,
                       sd.requires_credential, sd.credential_schema, ais.config
                FROM agent_instance_skills ais
                JOIN skill_definitions sd ON sd.id = ais.skill_id
                JOIN agent_instances ai ON ai.id = ais.instance_id
                WHERE ais.tenant_id = :tenant_id
                  AND ais.instance_id = :instance_id
                  AND ais.is_enabled = true
                  AND sd.is_active = true
                  AND ai.tenant_id = :tenant_id
                ORDER BY sd.slug
                """
            ),
            {"tenant_id": tenant_id, "instance_id": instance_id},
        )
        tools = await self.connection.execute(
            text(
                """
                SELECT td.slug, td.name, td.description, td.category, td.prompt_block,
                       td.schema, td.executor, td.is_builtin,
                       td.method, td.endpoint, td.headers_template, td.body_template,
                       td.variables_schema, ait.config
                FROM agent_instance_tools ait
                JOIN tool_definitions td ON td.id = ait.tool_id
                JOIN agent_instances ai ON ai.id = ait.instance_id
                WHERE ait.tenant_id = :tenant_id
                  AND ait.instance_id = :instance_id
                  AND ait.is_enabled = true
                  AND ai.tenant_id = :tenant_id
                ORDER BY td.slug
                """
            ),
            {"tenant_id": tenant_id, "instance_id": instance_id},
        )
        return {
            "tenant_id": tenant_id,
            "instance_id": instance_id,
            "skills": [dict(row._mapping) for row in skills.fetchall()],
            "tools": [dict(row._mapping) for row in tools.fetchall()],
        }


def _skill_definition(row) -> SkillDefinitionRecord:
    return SkillDefinitionRecord(
        id=row.id,
        slug=row.slug,
        name=row.name,
        description=row.description,
        category=row.category,
        prompt_block=row.prompt_block,
        tool_schema=row.tool_schema,
        executor=row.executor,
        input_schema=row.input_schema,
        output_schema=row.output_schema,
        requires_credential=row.requires_credential,
        credential_schema=row.credential_schema,
        is_active=row.is_active,
    )


def _tool_definition(row) -> ToolDefinitionRecord:
    return ToolDefinitionRecord(
        id=row.id,
        slug=row.slug,
        name=row.name,
        description=row.description,
        category=row.category,
        prompt_block=row.prompt_block,
        schema=row.schema,
        executor=row.executor,
        is_builtin=row.is_builtin,
        method=row.method,
        endpoint=row.endpoint,
        headers_template=row.headers_template or {},
        body_template=row.body_template,
        variables_schema=row.variables_schema or [],
    )


def _skill_activation(row) -> SkillActivationRecord:
    return SkillActivationRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        instance_id=row.instance_id,
        skill_id=row.skill_id,
        skill_slug=row.slug,
        is_enabled=row.is_enabled,
        config=row.config,
    )


def _tool_activation(row) -> ToolActivationRecord:
    return ToolActivationRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        instance_id=row.instance_id,
        tool_id=row.tool_id,
        tool_slug=row.slug,
        is_enabled=row.is_enabled,
        config=row.config,
    )


def _credential(row) -> CredentialRecord:
    credential_data = row.credential_data or {}
    return CredentialRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        skill_id=row.skill_id,
        skill_slug=row.slug,
        secret_ref=credential_data.get("secret_ref", ""),
        metadata=credential_data.get("metadata", {}),
    )
