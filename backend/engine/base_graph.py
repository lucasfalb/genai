from langgraph.graph import END, StateGraph

from engine.llm_client import complete_chat
from engine.state import AgentState


def rag_node(state: AgentState) -> AgentState:
    return {"retrieved_chunks": state.get("retrieved_chunks") or []}


async def llm_node(state: AgentState) -> AgentState:
    if state.get("final_response"):
        return {}

    system_prompt = state.get("system_prompt") or ""
    messages = state.get("messages") or []
    tool_schemas = state.get("tool_schemas") or []
    provider = state.get("ai_provider") or "openai"
    model = state.get("model") or "gpt-4.1-mini"
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
