# Stage 04 — Execution Engine, LangGraph e Redis Lock

_Fonte canônica: [`../platform_technical_spec.md`](../platform_technical_spec.md). Este stage reorganiza o conteúdo técnico sem substituir a especificação completa._

## Objetivo

Definir o runtime de execução do agente base: estado, bootstrap, grafo LangGraph, streaming SSE, persistência de sessão e serialização concorrente por `session_id`.

### Endpoint de chat com streaming SSE

```python
# api/v1/agent/chat.py

@router.post("/instances/{instance_id}/chat")
async def chat(
    instance_id: UUID,
    body: ChatRequest,
    request: Request,
    context: AgentContext = Depends(verify_agent_api_key)
):
    executor = AgentExecutor(
        instance_id=instance_id,
        tenant_id=context.tenant_id,
    )

    async def event_stream():
        run = executor.start_stream(
            message=body.message,
            session_id=body.session_id,
        )
        async for event in run:
            if await request.is_disconnected():
                await run.cancel()
                break
            yield f"data: {event.to_json()}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
```

---

### AgentState

```python
# engine/state.py

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    handoff_summary: Optional[str]

    # Contexto da sessão
    session_id: str
    tenant_id: str
    instance_id: str
    channel: str

    # Prompt montado para esta execução
    system_prompt: str

    # Capabilities calculadas no bootstrap
    available_tools: List[str]        # tools ativas na instância
    available_skills: List[str]       # skills ativas na instância
    tool_schemas: List[dict]          # schemas enviados ao LLM
    linked_agents: List[dict]         # agentes vinculados como tools fantasma

    # RAG
    rag_scope: List[str]              # collection_ids habilitadas
    retrieved_chunks: List[dict]

    # Execução
    pending_tool_calls: Optional[List[dict]]
    tool_results: Optional[List[dict]]
    handoff_target: Optional[str]     # instance_id para hand-off

    # Output
    final_response: Optional[str]
    citations: Optional[List[dict]]
```

### Bootstrap de run

```python
# engine/executor.py

class RunBootstrap:
    async def prepare(self, instance_id: str, tenant_id: str, session_id: str) -> AgentState:
        prompt = await PromptBuilder(self.db, self.redis).build(instance_id, tenant_id)

        metadata = await ToolMetadataCache(self.db, self.redis).get(
            tenant_id=tenant_id,
            instance_id=instance_id,
        )
        active_skills = metadata.active_skills
        active_tools = metadata.active_tools
        linked_agents = metadata.linked_agents

        # Monta schemas de tools para o LLM
        tool_schemas = (
            [s.definition.tool_schema for s in active_skills] +
            [t.definition.schema for t in active_tools] +
            [self._build_handoff_schema(link) for link in linked_agents]
        )

        instance = await self.db.get_instance(instance_id, tenant_id)

        return AgentState(
            session_id=session_id,
            tenant_id=tenant_id,
            instance_id=instance_id,
            system_prompt=prompt.full,
            available_tools=[t.definition.slug for t in active_tools],
            available_skills=[s.definition.slug for s in active_skills],
            tool_schemas=tool_schemas,
            linked_agents=[self._link_to_dict(l) for l in linked_agents],
            rag_scope=instance.rag_scope,
            messages=[],
            handoff_summary=None,
            retrieved_chunks=[],
        )

    def _build_handoff_schema(self, link) -> dict:
        return {
            "name": link.transfer_tool_name,
            "description": link.trigger_description,
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Motivo da transferência"}
                },
                "required": ["reason"]
            }
        }
```

### Grafo LangGraph do agente base

```python
# engine/base_graph.py

from langgraph.graph import StateGraph, END
from engine.state import AgentState

def create_base_graph() -> StateGraph:
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
        }
    )

    graph.add_edge("dispatch", "llm")
    graph.add_edge("handoff", END)

    return graph.compile()

def route_after_llm(state: AgentState) -> str:
    calls = state.get("pending_tool_calls", [])
    if not calls:
        return "respond"
    # Verifica se é um hand-off
    for call in calls:
        if call["name"] in [l["transfer_tool_name"] for l in state["linked_agents"]]:
            return "handoff"
    return "tool_call"
```

---

### SessionManager e ResponseManager

O `SessionManager` normaliza entradas vindas de API, Widget, Webhook e WhatsApp para o mesmo contrato interno: `tenant_id`, `instance_id`, `session_id`, `channel`, `sender_id`, `metadata` e mensagem do usuário. Isso mantém o LangGraph independente do canal de origem.

O `ResponseManager` centraliza a etapa final do run: persiste a resposta, envia eventos SSE quando aplicável, registra métricas e aciona integrações assíncronas como o Outbound Data Bridge.

### Concorrência por sessão

Cada `session_id` deve ter no máximo uma execução ativa por vez. Antes de carregar ou gravar estado no checkpointer do LangGraph, o backend adquire um lock distribuído no Redis:

- Chave: `session:{tenant_id}:{session_id}:lock`.
- Aquisição atômica: `SET key run_id NX EX 45`.
- Renovação durante streaming longo.
- Liberação segura apenas se o valor ainda for o mesmo `run_id`.
- Se o lock já existir, a API retorna `409 Conflict` ou enfileira a mensagem em `session:{tenant_id}:{session_id}:queue`, conforme configuração do canal.

O checkpointer mantém `thread_id = session_id`, mas as escritas são serializadas pelo lock. Além disso, cada mensagem persistida recebe `sequence_no` incremental por sessão, garantindo ordenação estável mesmo quando duas requisições chegam quase ao mesmo tempo.

```python
# engine/session_lock.py

class SessionLock:
    async def acquire(self, tenant_id: str, session_id: str, run_id: str) -> bool:
        key = f"session:{tenant_id}:{session_id}:lock"
        return bool(await self.redis.set(key, run_id, nx=True, ex=45))

    async def release(self, tenant_id: str, session_id: str, run_id: str) -> None:
        key = f"session:{tenant_id}:{session_id}:lock"
        await self.redis.eval(
            """
            if redis.call("GET", KEYS[1]) == ARGV[1] then
                return redis.call("DEL", KEYS[1])
            end
            return 0
            """,
            1,
            key,
            run_id,
        )
```

## Implementacao Stage 04

- `engine/state.py`, `engine/bootstrap.py`, `engine/session_lock.py` e `engine/executor.py` criam a fundacao do runtime.
- `engine/base_graph.py` compila o grafo LangGraph base com nodes `rag`, `llm`, `dispatch` e `handoff`.
- O endpoint `/api/v1/agent/instances/{instance_id}/chat` usa Bearer auth, `X-Tenant-ID`, permissao `INTERACT_WITH_AGENTS`, lock por sessao e retorna SSE.
- O endpoint prepara o run antes do `StreamingResponse`, mantendo conexao e lock durante o stream para permitir cancelamento em disconnect.
- A resposta atual do executor e deterministica e marcada como placeholder; LLM real fica para os stages de provider/prompt/RAG.
- O lock implementa acquire com `SET NX EX`, renovacao por compare-and-expire e release seguro por compare-and-delete.
