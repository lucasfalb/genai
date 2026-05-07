from typing import TypedDict


class AgentState(TypedDict, total=False):
    messages: list[dict]
    handoff_summary: str | None
    session_id: str
    tenant_id: str
    instance_id: str
    channel: str
    model: str
    temperature: float
    ai_api_key: str
    ai_base_url: str | None
    system_prompt: str
    available_tools: list[str]
    available_skills: list[str]
    tool_schemas: list[dict]
    linked_agents: list[dict]
    rag_scope: list[str]
    retrieved_chunks: list[dict]
    pending_tool_calls: list[dict] | None
    tool_results: list[dict] | None
    handoff_target: str | None
    final_response: str | None
    citations: list[dict] | None
