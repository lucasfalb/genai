import json

from langgraph.graph import END, StateGraph

from engine.state import AgentState


def _get_openai_client(*, api_key: str, base_url: str | None):
    from openai import AsyncOpenAI
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


def rag_node(state: AgentState) -> AgentState:
    return {"retrieved_chunks": state.get("retrieved_chunks") or []}


async def llm_node(state: AgentState) -> AgentState:
    if state.get("final_response"):
        return {}

    system_prompt = state.get("system_prompt") or ""
    messages = state.get("messages") or []
    tool_schemas = state.get("tool_schemas") or []
    model = state.get("model") or "gpt-4.1-mini"
    temperature = state.get("temperature", 0.2)
    api_key = state.get("ai_api_key") or ""
    base_url = state.get("ai_base_url")

    openai_messages = [{"role": "system", "content": system_prompt}] + list(messages)

    kwargs: dict = {
        "model": model,
        "temperature": temperature,
        "messages": openai_messages,
    }
    if tool_schemas:
        kwargs["tools"] = [{"type": "function", "function": s} for s in tool_schemas]
        kwargs["tool_choice"] = "auto"

    client = _get_openai_client(api_key=api_key, base_url=base_url)
    response = await client.chat.completions.create(**kwargs)
    choice = response.choices[0]

    if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
        tool_calls = [
            {
                "name": tc.function.name,
                "arguments": json.loads(tc.function.arguments or "{}"),
                "id": tc.id,
            }
            for tc in choice.message.tool_calls
        ]
        return {"pending_tool_calls": tool_calls}

    return {"final_response": choice.message.content or ""}


def dispatch_node(state: AgentState) -> AgentState:
    return {"tool_results": state.get("tool_results") or []}


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


def create_base_graph():
    graph = StateGraph(AgentState)
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
