from __future__ import annotations

import inspect
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.registry_cache import ToolMetadataCache
from engine.prompt_cache import PromptCache
from engine.prompt_sanitizer import PromptSanitizer
from engine.prompt_schema import SystemPrompt


class PromptBuilder:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def build(
        self,
        *,
        tenant_id: UUID,
        instance_id: UUID,
        core_prompt: str,
        linked_agents: list[dict] | None = None,
    ) -> SystemPrompt:
        cached = await PromptCache(self.connection).get(tenant_id=tenant_id, instance_id=instance_id)
        if cached is not None:
            return cached

        metadata = await ToolMetadataCache(self.connection).get(
            tenant_id=tenant_id, instance_id=instance_id
        )
        prompt_config = await self._get_prompt_config(tenant_id=tenant_id, instance_id=instance_id)
        sp = PromptBuilder.assemble(
            core_prompt=core_prompt,
            instruction_blocks=prompt_config["instruction_blocks"],
            guardrails=prompt_config["guardrails"],
            constraints=prompt_config["constraints"],
            skills=metadata.skills,
            tools=metadata.tools,
            linked_agents=linked_agents or [],
        )
        validated_prompt = PromptSanitizer().validate(
            sp,
            metadata={
                "skills": metadata.skills,
                "tools": metadata.tools,
                "linked_agents": linked_agents or [],
                "instruction_blocks": prompt_config["instruction_blocks"],
                "guardrails": prompt_config["guardrails"],
                "constraints": prompt_config["constraints"],
            },
        )
        await PromptCache(self.connection).set(tenant_id=tenant_id, instance_id=instance_id, prompt=validated_prompt)
        return validated_prompt

    @staticmethod
    def assemble(
        *,
        core_prompt: str,
        instruction_blocks: list[dict] | None = None,
        guardrails: list[dict] | None = None,
        constraints: list[dict] | None = None,
        skills: list,
        tools: list,
        linked_agents: list[dict] | None = None,
    ) -> SystemPrompt:
        core = core_prompt.strip()
        instruction_text = _format_instruction_blocks(instruction_blocks or [])
        guardrail_text = _format_guardrails(guardrails or [])
        constraints_text = _format_constraints(constraints or [])
        tool_parts: list[str] = []

        if skills:
            blocks = "\n\n".join(s.prompt_block.strip() for s in skills)
            tool_parts.append(f"### Habilidades Disponíveis\n{blocks}")
        if tools:
            blocks = "\n\n".join(t.prompt_block.strip() for t in tools)
            tool_parts.append(f"### Ferramentas Disponíveis\n{blocks}")
        if linked_agents:
            lines = [
                f"- `{la['transfer_tool_name']}`: {la['trigger_description']}"
                for la in linked_agents
            ]
            tool_parts.append("### Hand-off de Agentes\n" + "\n".join(lines))

        tool_instructions = "\n\n".join(tool_parts)
        full = "\n\n".join(
            filter(None, [core, instruction_text, tool_instructions, guardrail_text, constraints_text])
        ).strip()

        return SystemPrompt(
            core=core,
            instruction_blocks=instruction_text,
            tool_instructions=tool_instructions,
            guardrails=guardrail_text,
            constraints=constraints_text,
            full=full,
        )

    async def _get_prompt_config(self, *, tenant_id: UUID, instance_id: UUID) -> dict[str, list[dict]]:
        result_or_awaitable = self.connection.execute(
            text(
                """
                SELECT instruction_blocks, guardrails, constraints
                FROM agent_instances
                WHERE tenant_id = :tenant_id AND id = :instance_id
                """
            ),
            {"tenant_id": tenant_id, "instance_id": instance_id},
        )
        if not inspect.isawaitable(result_or_awaitable):
            return {"instruction_blocks": [], "guardrails": [], "constraints": []}
        result = await result_or_awaitable
        row = result.one_or_none()
        if row is None:
            return {"instruction_blocks": [], "guardrails": [], "constraints": []}
        return {
            "instruction_blocks": row.instruction_blocks or [],
            "guardrails": row.guardrails or [],
            "constraints": getattr(row, "constraints", None) or [],
        }


def _format_instruction_blocks(blocks: list[dict]) -> str:
    enabled = [block for block in blocks if block.get("is_enabled", True)]
    if not enabled:
        return ""
    ordered = sorted(enabled, key=lambda item: (item.get("priority", 100), item.get("topic", ""), item.get("id", "")))
    lines: list[str] = ["### Instrucoes por Topico"]
    for block in ordered:
        lines.append(
            f"#### {block.get('topic', 'geral')} - {block.get('title', block.get('id', 'instrucao'))}\n"
            f"{str(block.get('content', '')).strip()}"
        )
    return "\n\n".join(lines).strip()


def _format_constraints(constraints: list[dict]) -> str:
    enabled = [c for c in constraints if c.get("is_enabled", True)]
    if not enabled:
        return ""
    ordered = sorted(enabled, key=lambda item: (item.get("priority", 100), item.get("id", "")))
    lines = ["### Restrições"]
    for item in ordered:
        rule = str(item.get("rule", "")).strip()
        if rule:
            lines.append(f"- {rule}")
    return "\n".join(lines).strip() if len(lines) > 1 else ""


def _format_guardrails(guardrails: list[dict]) -> str:
    enabled = [guardrail for guardrail in guardrails if guardrail.get("is_enabled", True)]
    if not enabled:
        return ""
    severity_order = {"blocking": 0, "critical": 1, "warning": 2, "info": 3}
    ordered = sorted(
        enabled,
        key=lambda item: (severity_order.get(item.get("severity", "critical"), 1), item.get("category", ""), item.get("id", "")),
    )
    lines = ["### Guardrails Customizados"]
    for guardrail in ordered:
        lines.append(
            f"- [{guardrail.get('severity', 'critical')}] "
            f"{guardrail.get('category', 'geral')}: {str(guardrail.get('rule', '')).strip()}"
        )
    return "\n".join(lines).strip()
