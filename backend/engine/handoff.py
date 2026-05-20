from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class HandoffSummary(BaseModel):
    source_instance_id: UUID | str
    target_instance_id: UUID | str
    reason: str
    user_goal: str = ""
    known_facts: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    actions_already_taken: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)
    custom_instructions: str | None = None


class HandoffSanitizer:
    @staticmethod
    def keep_recent_conversation(messages: list[dict], max_messages: int = 8) -> list[dict]:
        allowed_roles = {"user", "assistant", "human", "ai"}
        clean: list[dict] = []
        for message in messages or []:
            role = str(message.get("role") or message.get("type") or "").lower()
            if role not in allowed_roles:
                continue
            if message.get("tool_calls") or message.get("tool_call_id"):
                continue
            clean.append({"role": _normalize_role(role), "content": str(message.get("content") or "")})
        return clean[-max(0, max_messages) :]


class HandoffSummarizer:
    async def summarize(
        self,
        *,
        messages: list[dict],
        reason: str,
        source_instance_id: str,
        target_instance_id: str,
        custom_instructions: str | None = None,
    ) -> HandoffSummary:
        user_messages = [str(m.get("content") or "") for m in messages if m.get("role") == "user"]
        assistant_messages = [str(m.get("content") or "") for m in messages if m.get("role") == "assistant"]
        user_goal = user_messages[-1] if user_messages else reason
        return HandoffSummary(
            source_instance_id=source_instance_id,
            target_instance_id=target_instance_id,
            reason=reason,
            user_goal=user_goal,
            known_facts=[item for item in user_messages[-3:] if item],
            actions_already_taken=[item for item in assistant_messages[-3:] if item],
            custom_instructions=custom_instructions,
        )


def build_handoff_messages(
    *,
    summary: HandoffSummary,
    sanitized_messages: list[dict],
    context_policy: dict[str, Any],
) -> list[dict]:
    messages: list[dict] = []
    if context_policy.get("include_handoff_summary", True):
        summary_text = [
            "Handoff context from the previous agent.",
            f"Reason: {summary.reason}",
            f"User goal: {summary.user_goal}",
        ]
        if summary.custom_instructions:
            summary_text.append(f"Custom instructions: {summary.custom_instructions}")
        if summary.known_facts:
            summary_text.append("Known facts:\n" + "\n".join(f"- {item}" for item in summary.known_facts))
        if summary.actions_already_taken:
            summary_text.append(
                "Actions already taken:\n" + "\n".join(f"- {item}" for item in summary.actions_already_taken)
            )
        messages.append({"role": "user", "content": "\n\n".join(summary_text)})
    if context_policy.get("include_recent_messages", True):
        messages.extend(sanitized_messages)
    return messages


def _normalize_role(role: str) -> str:
    if role == "human":
        return "user"
    if role == "ai":
        return "assistant"
    return role
