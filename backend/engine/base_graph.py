import contextvars
import json
import re
from typing import Any, Callable

import httpx
from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncConnection

from engine.llm_client import complete_chat
from engine.nodes.rag_node import create_rag_node
from engine.state import AgentState


delta_sink_var: contextvars.ContextVar[Callable[[str], None] | None] = contextvars.ContextVar(
    "delta_sink", default=None
)


async def _noop_rag_node(state: AgentState) -> AgentState:
    return {"retrieved_chunks": state.get("retrieved_chunks") or []}


async def llm_node(state: AgentState) -> AgentState:
    if state.get("final_response"):
        return {}

    system_prompt = state.get("system_prompt") or ""
    messages = state.get("messages") or []
    tool_schemas = state.get("tool_schemas") or []
    provider = state.get("ai_provider") or "openai"
    model = state.get("model") or "gpt-5-mini"
    temperature = state.get("temperature", 0.2)
    api_key = state.get("ai_api_key") or ""

    iterations = state.get("tool_call_iterations") or 0
    force_finalize = iterations >= MAX_TOOL_ITERATIONS

    on_delta = delta_sink_var.get()

    openai_messages = [{"role": "system", "content": system_prompt}] + list(messages)
    completion = await complete_chat(
        provider=provider,
        api_key=api_key,
        model=model,
        temperature=temperature,
        messages=openai_messages,
        tool_schemas=[] if force_finalize else tool_schemas,
        on_delta=on_delta,
    )

    current_usage = state.get("token_usage") or {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "llm_calls": 0,
        "per_call": [],
    }
    call_usage = {
        "prompt_tokens": completion.usage.prompt_tokens,
        "completion_tokens": completion.usage.completion_tokens,
        "total_tokens": completion.usage.total_tokens,
        "model": model,
        "phase": "tool_call" if completion.pending_tool_calls else "final",
        "iteration": iterations,
        "output_text": completion.final_response,
        "tool_calls": completion.pending_tool_calls or [],
    }
    next_usage = {
        "prompt_tokens": current_usage["prompt_tokens"] + completion.usage.prompt_tokens,
        "completion_tokens": current_usage["completion_tokens"] + completion.usage.completion_tokens,
        "total_tokens": current_usage["total_tokens"] + completion.usage.total_tokens,
        "llm_calls": current_usage["llm_calls"] + 1,
        "per_call": list(current_usage.get("per_call") or []) + [call_usage],
    }

    if completion.pending_tool_calls and not force_finalize:
        return {"pending_tool_calls": completion.pending_tool_calls, "token_usage": next_usage}
    return {"final_response": completion.final_response or "", "token_usage": next_usage}


_PLACEHOLDER_RE = re.compile(r"\{([\w.]+)\}")


def _substitute(template: str, sources: list[dict]) -> str:
    def resolve(match: re.Match[str]) -> str:
        key = match.group(1)
        for src in sources:
            if key in src:
                value = src[key]
                return "" if value is None else str(value)
        return ""

    return _PLACEHOLDER_RE.sub(resolve, template)


def _substitute_headers(template: dict, sources: list[dict]) -> dict:
    return {k: _substitute(str(v), sources) for k, v in (template or {}).items()}


async def _execute_web_fetch(call: dict, config: dict | None = None) -> dict:
    args = call.get("arguments") or {}
    tool_name = call.get("name", "")
    config = config or {}
    http_override = config.get("http_override") or {}
    variables = config.get("variables") or {}
    sources = [args, variables]

    endpoint_template = (
        http_override.get("endpoint")
        or config.get("endpoint")
        or args.get("url")
        or ""
    )
    url = _substitute(endpoint_template, sources) if endpoint_template else ""

    if not url:
        return {"name": tool_name, "output": json.dumps({"error": "No URL configured for tool"}), "id": call.get("id")}

    method = (
        http_override.get("method")
        or args.get("method")
        or config.get("method")
        or "GET"
    ).upper()

    headers_template = (
        http_override.get("headers")
        or config.get("headers_template")
        or args.get("headers")
        or {}
    )
    headers = _substitute_headers(headers_template, sources)

    body_template = http_override.get("body") or config.get("body_template")
    if body_template:
        body = _substitute(body_template, sources)
    else:
        body = args.get("body")

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            if method in {"POST", "PUT", "PATCH"}:
                resp = await client.request(method, url, headers=headers, content=body)
            elif method == "DELETE":
                resp = await client.delete(url, headers=headers)
            else:
                resp = await client.get(url, headers=headers)

            content_type = resp.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    output = resp.json()
                except Exception:
                    output = resp.text
            else:
                output = resp.text

            return {
                "name": tool_name,
                "output": json.dumps({"status": resp.status_code, "data": output}, ensure_ascii=False),
                "id": call.get("id"),
            }
    except Exception as e:
        return {
            "name": tool_name,
            "output": json.dumps({"error": str(e)}, ensure_ascii=False),
            "id": call.get("id"),
        }


TOOL_EXECUTORS: dict[str, Any] = {
    "web_fetch": _execute_web_fetch,
}


MAX_TOOL_ITERATIONS = 5
MAX_TOOL_OUTPUT_CHARS = 8000


def _truncate_tool_output(output: str) -> str:
    if not output or len(output) <= MAX_TOOL_OUTPUT_CHARS:
        return output
    return output[:MAX_TOOL_OUTPUT_CHARS] + f"\n...[truncated {len(output) - MAX_TOOL_OUTPUT_CHARS} chars]"


async def dispatch_node(state: AgentState) -> AgentState:
    calls = state.get("pending_tool_calls") or []
    tool_configs = state.get("tool_configs") or {}
    available_skills = set(state.get("available_skills") or [])
    results: list[dict] = []
    for call in calls:
        name = call.get("name", "")
        tool_config = tool_configs.get(name) or {}
        executor_key = tool_config.get("executor") or name
        executor = TOOL_EXECUTORS.get(executor_key) or TOOL_EXECUTORS.get("web_fetch")
        if executor:
            result = await executor(call, tool_config)
            results.append(result)
        else:
            results.append({
                "name": name,
                "output": json.dumps({"error": f"No executor for tool: {name}"}),
                "id": call.get("id"),
            })

    messages = list(state.get("messages") or [])
    messages.append({
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": call.get("id"),
                "type": "function",
                "function": {
                    "name": call.get("name", ""),
                    "arguments": json.dumps(call.get("arguments") or {}, ensure_ascii=False),
                },
            }
            for call in calls
        ],
    })
    for res in results:
        messages.append({
            "role": "tool",
            "tool_call_id": res.get("id"),
            "content": _truncate_tool_output(res.get("output", "") or ""),
        })

    history = list(state.get("executed_tool_calls") or [])
    iteration = (state.get("tool_call_iterations") or 0) + 1
    by_id = {res.get("id"): res for res in results}
    for call in calls:
        name = call.get("name", "")
        result = by_id.get(call.get("id")) or {}
        history.append({
            "id": call.get("id"),
            "name": name,
            "kind": "skill" if name in available_skills else "tool",
            "arguments": call.get("arguments") or {},
            "output": result.get("output"),
            "error": result.get("error"),
            "iteration": iteration,
        })

    return {
        "tool_results": results,
        "executed_tool_calls": history,
        "messages": messages,
        "pending_tool_calls": None,
        "tool_call_iterations": iteration,
    }


def handoff_node(state: AgentState) -> AgentState:
    calls = state.get("pending_tool_calls") or []
    linked_tools = {link["transfer_tool_name"]: link for link in state.get("linked_agents") or []}
    for call in calls:
        if call.get("name") in linked_tools:
            target = linked_tools[call["name"]]["target_instance_id"]
            return {
                "handoff_target": target,
                "handoff_summary": call.get("arguments", {}).get("reason"),
            }
    return {}


def route_after_llm(state: AgentState) -> str:
    calls = state.get("pending_tool_calls") or []
    if not calls:
        return "respond"

    if (state.get("tool_call_iterations") or 0) >= MAX_TOOL_ITERATIONS:
        return "respond"

    linked_tool_names = {link["transfer_tool_name"] for link in state.get("linked_agents") or []}
    if any(call.get("name") in linked_tool_names for call in calls):
        return "handoff"
    return "tool_call"


def create_base_graph(*, connection: AsyncConnection | None = None):
    graph = StateGraph(AgentState)
    rag_node = create_rag_node(connection) if connection else _noop_rag_node
    graph.add_node("rag", rag_node)
    graph.add_node("llm", llm_node)
    graph.add_node("dispatch", dispatch_node)
    graph.add_node("handoff", handoff_node)

    graph.set_entry_point("rag")
    graph.add_edge("rag", "llm")
    graph.add_conditional_edges(
        "llm",
        route_after_llm,
        {
            "tool_call": "dispatch",
            "handoff": "handoff",
            "respond": END,
        },
    )
    graph.add_edge("dispatch", "llm")
    graph.add_edge("handoff", END)
    return graph.compile()
