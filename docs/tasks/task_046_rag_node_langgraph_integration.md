# Task: TASK-046 - RAG Node Integration no LangGraph

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-046 |
| **Group** | RAG |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_06_rag.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

O grafo LangGraph ja tem um node `rag` registrado mas sem implementacao real. Esta task substitui o placeholder pelo `TenantRetriever` e injeta os chunks recuperados no contexto do `llm_node` via `AgentState.retrieved_chunks`.

## Objectives

- [ ] Reescrever `engine/nodes/rag_node.py` usando `TenantRetriever`.
- [ ] Popular `AgentState.retrieved_chunks` com resultados do retriever.
- [ ] Injetar chunks como contexto no `system_prompt` ou como mensagem de contexto antes do LLM call.
- [ ] Manter `rag_scope` do `AgentState` (vem do bootstrap via `instance.rag_scope`).
- [ ] Testar: chunks injetados no prompt, rag_scope vazio nao chama retriever.

## Non-Goals

- Reranking ou fusion de resultados.
- Exibir citations ao usuario (pode ser feito em task futura).

## Stage Boundaries

Apenas o node `rag` e integracao com `llm_node`. Nenhum endpoint novo.

## Dependencies

- TASK-045 (TenantRetriever)
- TASK-039 (llm_node real — consome o prompt com contexto RAG)

## Inputs & Contracts

- **Inputs**: `AgentState.messages[-1]` (ultima mensagem do usuario), `AgentState.rag_scope`, `AgentState.tenant_id`.
- **Outputs**: `AgentState.retrieved_chunks` preenchido; `AgentState.system_prompt` pode incluir secao de contexto RAG.
- **Schemas**: `retrieved_chunks: list[{text, source, score}]`.

## Constraints & Rules

1. `rag_scope = []` retorna imediatamente sem chamar retriever.
2. Chunks injetados como secao `### Contexto Relevante` antes do prompt de constraints.
3. Maximo de 5 chunks por execucao (top_k = 5).
4. Chunks nao devem incluir metadados internos de Qdrant (apenas `text` e `source`).

## Implementation Checklist

- [ ] Reescrever `engine/nodes/rag_node.py` com chamada real ao `TenantRetriever`.
- [ ] Montar secao de contexto e injetar em `AgentState.system_prompt` ou como mensagem.
- [ ] Testar node isolado: chunks populados, rag_scope vazio retorna estado inalterado.

## Acceptance Criteria

- [ ] Com `rag_scope` preenchido, `retrieved_chunks` nao vazio apos `rag_node`.
- [ ] `rag_scope = []` nao chama Qdrant.
- [ ] Contexto RAG visivel no prompt enviado ao LLM.

## Verification

```bash
cd backend
pytest tests/test_stage_06_rag_node.py
```

## Risks & Rollback

- **Risks**: chunks irrelevantes aumentam uso de tokens e podem confundir o LLM.
- **Rollback**: substituir `rag_node` por no-op que retorna estado inalterado.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para integracao do RAG node real no LangGraph.
