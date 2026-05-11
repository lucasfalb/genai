import asyncio
import json
import time
from typing import Any, Callable

import httpx
from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncConnection

from engine.llm_client import complete_chat
from engine.nodes.rag_node import create_rag_node
from engine.state import AgentState


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

    openai_messages = [{"role": "system", "content": system_prompt}] + list(messages)
    completion = await complete_chat(
        provider=provider,
        api_key=api_key,
        model=model,
        temperature=temperature,
        messages=openai_messages,
        tool_schemas=tool_schemas,
    )

    if completion.pending_tool_calls:
        return {"pending_tool_calls": completion.pending_tool_calls}
    return {"final_response": completion.final_response or ""}


async def _execute_web_fetch(call: dict) -> dict:
    args = call.get("arguments") or {}
    url = args.get("url", "")
    if not url:
        return {"name": "web_fetch", "output": json.dumps({"error": "No URL provided"}), "id": call.get("id")}

    method = (args.get("method") or "GET").upper()
    headers = args.get("headers") or {}
    body = args.get("body")

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            if method == "POST":
                resp = await client.post(url, headers=headers, content=body)
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
                "name": "web_fetch",
                "output": json.dumps({"status": resp.status_code, "data": output}, ensure_ascii=False),
                "id": call.get("id"),
            }
    except Exception as e:
        return {
            "name": "web_fetch",
            "output": json.dumps({"error": str(e)}, ensure_ascii=False),
            "id": call.get("id"),
        }


TOOL_EXECUTORS: dict[str, Any] = {
    "web_fetch": _execute_web_fetch,
}


async def dispatch_node(state: AgentState) -> AgentState:
    calls = state.get("pending_tool_calls") or []
    results: list[dict] = []
    for call in calls:
        name = call.get("name", "")
        executor = TOOL_EXECUTORS.get(name)
        if executor:
            result = await executor(call)
            results.append(result)
        else:
            results.append({
                "name": name,
                "output": json.dumps({"error": f"No executor for tool: {name}"}),
                "id": call.get("id"),
            })
    return {"tool_results": results}


def handoff_node(state: AgentState) -> AgentState:
    calls = state.get("pending_tool_calls") or []
    linked_tools = {link["transfer_tool_name"]: link for link in state.get("linked_agents") or []}
    for call in calls:
        if call.get("name") in linked_tools:
            return {
                "handoff_target": linked_tools[call["name"]]["target_instance_id"],
                "handoff_summary": call.get("arguments", {}).get("reason"),
            }
    return {}


def route_after_llm(state: AgentState) -> str:
    calls = state.get("pending_tool_calls") or []
    if not calls:
        return "respond"

    linked_tool_names = {link["transfer_tool_name"] for link in state.get("linked_agents") or []}
    if any(call.get("name") in linked_tool_names for call in calls):
        return "handoff"
    return "tool_call"


def _instrument(name: str, fn: Callable, timings: list[dict] | None):
    if timings is None:
        return fn

    if asyncio.iscoroutinefunction(fn):
        async def inner_async(state):
            t0 = time.perf_counter()
            try:
                return await fn(state)
            finally:
                timings.append(
                    {"name": name, "duration_ms": int((time.perf_counter() - t0) * 1000)}
                )
        return inner_async

    def inner_sync(state):
        t0 = time.perf_counter()
        try:
            return fn(state)
        finally:
            timings.append(
                {"name": name, "duration_ms": int((time.perf_counter() - t0) * 1000)}
            )
    return inner_sync


def create_base_graph(
    *,
    connection: AsyncConnection | None = None,
    node_timings: list[dict] | None = None,
):
    graph = StateGraph(AgentState)
    rag_node = create_rag_node(connection) if connection else _noop_rag_node
    graph.add_node("rag", _instrument("rag", rag_node, node_timings))
    graph.add_node("llm", _instrument("llm", llm_node, node_timings))
    graph.add_node("dispatch", _instrument("dispatch", dispatch_node, node_timings))
    graph.add_node("handoff", _instrument("handoff", handoff_node, node_timings))

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
