from datetime import datetime
from typing import Any
from uuid import UUID

from engine.state import AgentState

SENSITIVE_KEYS = {"ai_api_key", "api_key", "api_key_encrypted", "authorization", "password", "secret", "token"}


def build_run_trace(
    *,
    run_id: str,
    tenant_id: UUID,
    instance_id: UUID,
    session_id: UUID,
    channel: str,
    bootstrap_state: AgentState,
    result_state: dict,
    user_message: str,
    final_response: str,
    started_at: datetime,
    completed_at: datetime,
    graph_steps: list[dict] | None = None,
) -> dict[str, Any]:
    sections = bootstrap_state.get("system_prompt_sections") or {}
    chunks = result_state.get("retrieved_chunks") or []
    pending = result_state.get("pending_tool_calls") or []
    tool_results = result_state.get("tool_results") or []
    executed = result_state.get("executed_tool_calls") or []
    token_usage = result_state.get("token_usage") or {}
    messages = result_state.get("messages") or bootstrap_state.get("messages") or []
    duration_ms = max(0, int((completed_at - started_at).total_seconds() * 1000))

    return _redact({
        "run_id": run_id,
        "tenant_id": str(tenant_id),
        "instance_id": str(instance_id),
        "session_id": str(session_id),
        "channel": channel,
        "user_message": user_message,
        "final_response": final_response,
        "messages": [_normalize_message(m) for m in messages],
        "model": bootstrap_state.get("model"),
        "temperature": bootstrap_state.get("temperature"),
        "ai_provider": bootstrap_state.get("ai_provider"),
        "system_prompt": bootstrap_state.get("system_prompt"),
        "system_prompt_sections": [
            {"label": "core", "content": sections.get("core", "")},
            {"label": "instruction_blocks", "content": sections.get("instruction_blocks", "")},
            {"label": "tool_instructions", "content": sections.get("tool_instructions", "")},
            {"label": "guardrails", "content": sections.get("guardrails", "")},
            {"label": "constraints", "content": sections.get("constraints", "")},
        ],
        "available_tools": list(bootstrap_state.get("available_tools") or []),
        "available_skills": list(bootstrap_state.get("available_skills") or []),
        "tool_schemas": list(bootstrap_state.get("tool_schemas") or []),
        "linked_agents": list(bootstrap_state.get("linked_agents") or []),
        "rag_scope": list(bootstrap_state.get("rag_scope") or []),
        "retrieved_chunks": [_normalize_chunk(c) for c in chunks],
        "pending_tool_calls": [_normalize_tool_call(c) for c in pending],
        "tool_results": [_normalize_tool_result(r) for r in tool_results],
        "executed_tool_calls": [_normalize_executed_call(c) for c in executed],
        "token_usage": _normalize_token_usage(token_usage),
        "thinking": result_state.get("thinking"),
        "reasoning": result_state.get("reasoning"),
        "rag_error": result_state.get("rag_error"),
        "run_error": result_state.get("run_error"),
        "handoff_target": result_state.get("handoff_target") or result_state.get("_handoff_target"),
        "handoff_target_name": result_state.get("_handoff_target_name"),
        "handoff_summary": result_state.get("handoff_summary"),
        "handoff_context": result_state.get("_handoff_context"),
        "citations": list(result_state.get("citations") or []),
        "node_timings": list(graph_steps or []),
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_ms": duration_ms,
        "otel_trace_id": result_state.get("_otel_trace_id"),
    })


def _normalize_chunk(chunk: Any) -> dict:
    if not isinstance(chunk, dict):
        return {"text": str(chunk)}
    return {
        "text": chunk.get("text", ""),
        "source": chunk.get("source"),
        "score": chunk.get("score"),
        "collection_id": chunk.get("collection_id"),
        "document_id": chunk.get("document_id"),
        "filename": chunk.get("filename"),
    }


def _normalize_tool_call(call: Any) -> dict:
    if not isinstance(call, dict):
        return {"name": str(call)}
    return {
        "id": call.get("id"),
        "name": call.get("name") or call.get("tool"),
        "arguments": call.get("arguments") or call.get("args"),
    }


def _normalize_message(message: Any) -> dict:
    if not isinstance(message, dict):
        return {"role": "unknown", "content": str(message)}
    normalized = {
        "role": message.get("role") or "unknown",
        "content": message.get("content"),
    }
    if message.get("tool_call_id"):
        normalized["tool_call_id"] = message.get("tool_call_id")
    if message.get("tool_calls"):
        normalized["tool_calls"] = message.get("tool_calls")
    return normalized


def _normalize_tool_result(result: Any) -> dict:
    if not isinstance(result, dict):
        return {"output": str(result)}
    return {
        "id": result.get("id"),
        "name": result.get("name") or result.get("tool"),
        "output": result.get("output") or result.get("result"),
        "error": result.get("error"),
    }


def _normalize_token_usage(usage: Any) -> dict:
    if not isinstance(usage, dict):
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "llm_calls": 0,
            "embedding_tokens": 0,
            "embedding_calls": 0,
            "per_call": [],
        }
    return {
        "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
        "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0),
        "llm_calls": int(usage.get("llm_calls", 0) or 0),
        "embedding_tokens": int(usage.get("embedding_tokens", 0) or 0),
        "embedding_calls": int(usage.get("embedding_calls", 0) or 0),
        "per_call": list(usage.get("per_call") or []),
    }


def _normalize_executed_call(call: Any) -> dict:
    if not isinstance(call, dict):
        return {"name": str(call)}
    return {
        "id": call.get("id"),
        "name": call.get("name") or call.get("tool"),
        "kind": call.get("kind") or "tool",
        "arguments": call.get("arguments") or call.get("args"),
        "output": call.get("output"),
        "error": call.get("error"),
        "iteration": call.get("iteration"),
    }


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict = {}
        for key, val in value.items():
            if key.lower() in SENSITIVE_KEYS:
                cleaned[key] = "***" if val else None
                continue
            cleaned[key] = _redact(val)
        return cleaned
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value
