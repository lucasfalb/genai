# Task: TASK-039 - LLM Node e Provider Integration

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-039 |
| **Group** | ENGINE |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_05_prompts.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

O `llm_node` do grafo LangGraph atual retorna resposta placeholder. Esta task substitui o placeholder por uma chamada real ao LLM (OpenAI), usando o `SystemPrompt` montado pelo `PromptBuilder` e os `tool_schemas` do bootstrap para function calling.

## Objectives

- [ ] Configurar cliente OpenAI em `engine/llm_client.py` usando `OPENAI_API_KEY` do `.env`.
- [ ] Reescrever `llm_node` em `engine/nodes/llm_node.py` para chamar LLM real com `system_prompt` e `tool_schemas` do `AgentState`.
- [ ] Tratar resposta: texto livre vai para `final_response`; tool calls populam `pending_tool_calls`.
- [ ] Integrar `PromptBuilder.build()` no bootstrap (`engine/bootstrap.py`) para popular `system_prompt` no `AgentState`.
- [ ] Configurar `model` da instancia no cliente (default `gpt-4.1-mini`).
- [ ] Testar com mock de OpenAI: texto livre, tool call unico, multiplos tool calls.

## Non-Goals

- Suporte a multiplos providers (Anthropic, Gemini) nesta task.
- Streaming de tokens do LLM (SSE ja existe no endpoint — apenas result final aqui).
- RAG (TASK-046).

## Stage Boundaries

Apenas substituicao do node LLM e integracao do PromptBuilder no bootstrap. Nao cria endpoints.

## Dependencies

- TASK-037 (PromptBuilder — fonte do system_prompt)
- TASK-023 (base_graph — grafo onde llm_node esta registrado)

## Inputs & Contracts

- **Inputs**: `AgentState.messages`, `AgentState.system_prompt`, `AgentState.tool_schemas`, `AgentState.instance.model`.
- **Outputs**: `AgentState` com `final_response` (str) OU `pending_tool_calls` (list[dict]).
- **Schemas**: `tool_schemas` no formato OpenAI function calling.

## Constraints & Rules

1. `OPENAI_API_KEY` nunca aparece em logs ou traces.
2. `model` vem de `instance.model`; fallback para `gpt-4.1-mini` se None.
3. `temperature` vem de `instance.temperature`; fallback para `0.2`.
4. `pending_tool_calls` segue formato `[{"name": ..., "id": ..., "args": {...}}]`.
5. Erro do provider deve propagar como `HTTPException 502` no endpoint.

## Implementation Checklist

- [ ] Adicionar `openai` ao `pyproject.toml`.
- [ ] Criar `engine/llm_client.py` com `AsyncOpenAI` configurado.
- [ ] Reescrever `engine/nodes/llm_node.py` substituindo placeholder.
- [ ] Integrar `PromptBuilder.build()` em `engine/bootstrap.py` para popular `system_prompt`.
- [ ] Adicionar `OPENAI_API_KEY` ao `.env.example`.
- [ ] Testar llm_node com mock: resposta texto, resposta com tool call.

## Acceptance Criteria

- [ ] `llm_node` chama LLM real e popula `final_response` para resposta de texto.
- [ ] `llm_node` popula `pending_tool_calls` para tool call do LLM.
- [ ] `system_prompt` do `AgentState` vem do `PromptBuilder` no bootstrap.
- [ ] `OPENAI_API_KEY` ausente levanta erro de configuracao na inicializacao.

## Verification

```bash
cd backend
pytest tests/test_llm_node.py
# Teste de integracao real requer OPENAI_API_KEY valida
```

## Risks & Rollback

- **Risks**: custo de chamadas LLM em testes; latencia variavel em CI.
- **Rollback**: restaurar resposta placeholder no `llm_node` e mockar cliente.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para substituir executor placeholder por LLM real.
