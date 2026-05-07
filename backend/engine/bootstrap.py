from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.registry_cache import ToolMetadataCache
from engine.ai_provider import AIProviderResolver
from engine.prompt_builder import PromptBuilder
from engine.state import AgentState


class AgentInstanceNotFound(RuntimeError):
    pass


@dataclass(frozen=True)
class AgentInstanceRecord:
    id: UUID
    tenant_id: UUID
    core_prompt: str
    model: str
    temperature: float
    rag_scope: list


@dataclass(frozen=True)
class LinkedAgentRecord:
    id: UUID
    target_instance_id: UUID
    target_name: str
    transfer_tool_name: str
    trigger_description: str
    transfer_mode: str


class RunBootstrap:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def prepare(self, *, tenant_id: UUID, instance_id: UUID, session_id: UUID, channel: str) -> AgentState:
        instance = await self._get_instance(tenant_id=tenant_id, instance_id=instance_id)
        if instance is None:
            raise AgentInstanceNotFound("Agent instance not found")

        metadata = await ToolMetadataCache(self.connection).get(tenant_id=tenant_id, instance_id=instance_id)
        linked_agents = await self._get_linked_agents(tenant_id=tenant_id, instance_id=instance_id)
        system_prompt_obj = await PromptBuilder(self.connection).build(
            tenant_id=tenant_id,
            instance_id=instance_id,
            core_prompt=instance.core_prompt,
            linked_agents=[self._link_to_dict(link) for link in linked_agents],
        )
        messages = await self._get_messages(tenant_id=tenant_id, session_id=session_id)
        ai_config = await AIProviderResolver(self.connection).resolve(tenant_id=tenant_id)

        return AgentState(
            messages=messages,
            handoff_summary=None,
            session_id=str(session_id),
            tenant_id=str(tenant_id),
            instance_id=str(instance_id),
            channel=channel,
            model=instance.model,
            temperature=instance.temperature,
            ai_api_key=ai_config.api_key,
            ai_base_url=ai_config.base_url,
            system_prompt=system_prompt_obj.full,
            available_tools=[tool.slug for tool in metadata.tools],
            available_skills=[skill.slug for skill in metadata.skills],
            tool_schemas=[skill.tool_schema for skill in metadata.skills]
            + [tool.schema_ for tool in metadata.tools]
            + [self._build_handoff_schema(link) for link in linked_agents],
            linked_agents=[self._link_to_dict(link) for link in linked_agents],
            rag_scope=instance.rag_scope,
            retrieved_chunks=[],
            pending_tool_calls=None,
            tool_results=None,
            handoff_target=None,
            final_response=None,
            citations=None,
        )

    async def _get_instance(self, *, tenant_id: UUID, instance_id: UUID) -> AgentInstanceRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT id, tenant_id, core_prompt, model, temperature, rag_scope
                FROM agent_instances
                WHERE id = :instance_id AND tenant_id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id, "instance_id": instance_id},
        )
        row = result.one_or_none()
        if row is None:
            return None
        return AgentInstanceRecord(
            id=row.id,
            tenant_id=row.tenant_id,
            core_prompt=row.core_prompt,
            model=row.model,
            temperature=row.temperature,
            rag_scope=row.rag_scope or [],
        )

    async def _get_linked_agents(self, *, tenant_id: UUID, instance_id: UUID) -> list[LinkedAgentRecord]:
        result = await self.connection.execute(
            text(
                """
                SELECT al.id,
                       al.target_instance_id,
                       target.name AS target_name,
                       al.transfer_tool_name,
                       al.trigger_description,
                       al.transfer_mode
                FROM agent_links al
                JOIN agent_instances source
                  ON source.id = al.source_instance_id
                 AND source.tenant_id = al.tenant_id
                JOIN agent_instances target
                  ON target.id = al.target_instance_id
                 AND target.tenant_id = al.tenant_id
                WHERE al.tenant_id = :tenant_id
                  AND al.source_instance_id = :instance_id
                  AND al.is_enabled = true
                ORDER BY al.transfer_tool_name
                """
            ),
            {"tenant_id": tenant_id, "instance_id": instance_id},
        )
        return [
            LinkedAgentRecord(
                id=row.id,
                target_instance_id=row.target_instance_id,
                target_name=row.target_name,
                transfer_tool_name=row.transfer_tool_name,
                trigger_description=row.trigger_description,
                transfer_mode=row.transfer_mode,
            )
            for row in result.fetchall()
        ]

    async def _get_messages(self, *, tenant_id: UUID, session_id: UUID) -> list[dict]:
        result = await self.connection.execute(
            text(
                """
                SELECT role, content
                FROM messages
                WHERE session_id = :session_id AND tenant_id = :tenant_id
                ORDER BY sequence_no ASC
                LIMIT 50
                """
            ),
            {"session_id": session_id, "tenant_id": tenant_id},
        )
        return [{"role": row.role, "content": row.content} for row in result.fetchall()]

    @staticmethod
    def _build_handoff_schema(link: LinkedAgentRecord) -> dict:
        return {
            "name": link.transfer_tool_name,
            "description": link.trigger_description,
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Reason for transferring the conversation to the linked agent.",
                    }
                },
                "required": ["reason"],
            },
        }

    @staticmethod
    def _link_to_dict(link: LinkedAgentRecord) -> dict:
        return {
            "id": str(link.id),
            "target_instance_id": str(link.target_instance_id),
            "target_name": link.target_name,
            "transfer_tool_name": link.transfer_tool_name,
            "trigger_description": link.trigger_description,
            "transfer_mode": link.transfer_mode,
        }
