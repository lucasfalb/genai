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
    ai_provider: str
    ai_api_key: str
    system_prompt: str
    system_prompt_sections: dict
    available_tools: list[str]
    available_skills: list[str]
    tool_schemas: list[dict]
    tool_configs: dict
    linked_agents: list[dict]
    rag_scope: list[str]
    retrieved_chunks: list[dict]
    pending_tool_calls: list[dict] | None
    tool_results: list[dict] | None
    executed_tool_calls: list[dict]
    tool_call_iterations: int
    handoff_target: str | None
    final_response: str | None
    citations: list[dict] | None
    token_usage: dict
    rag_error: str | None
