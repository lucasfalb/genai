# Task: TASK-045 - TenantRetriever com RBAC e rag_scope

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-045 |
| **Group** | RAG |
| **Status** | DONE |
| **Stage Ref** | `docs/stages/stage_06_rag.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

O `TenantRetriever` e responsavel por buscar chunks relevantes no Qdrant dado um query, restringindo a busca as collections em `rag_scope` da instancia e apenas aquelas com `indexing_status` pesquisavel (`ready`, `partial`, `indexing`).

## Objectives

- [x] Implementar `TenantRetriever` em `rag/retriever.py`.
- [x] Filtrar `rag_scope` da instancia contra `indexing_status` pesquisavel no banco.
- [x] Gerar embedding do query via OpenAI.
- [x] Chamar Qdrant com filtro `must[tenant_id, collection_id in ready_scope, document_status=indexed]`.
- [x] Retornar lista de `{text, source, score}`.
- [x] Retornar `[]` se `rag_scope` vazio ou nenhuma collection pesquisavel.
- [x] Testar com Qdrant mockado: retorno correto, scope vazio, nenhuma collection ready, isolamento cross-tenant.

## Non-Goals

- Integracao com LangGraph (TASK-046).
- Reranking de resultados.

## Stage Boundaries

Apenas logica de recuperacao. Nao cria endpoints.

## Dependencies

- TASK-041 (repositorios — `get_searchable_collections`)
- TASK-015 (ToolMetadataCache — `rag_scope` da instancia vem do metadata)

## Inputs & Contracts

- **Inputs**: `query: str`, `tenant_id: str`, `rag_scope: list[str]`, `top_k: int = 5`.
- **Outputs**: `list[dict]` com `{text, source, score}`.
- **Schemas**: Qdrant query filter com `tenant_id` e `collection_id`.

## Constraints & Rules

1. Apenas collections com `indexing_status in (ready, partial, indexing)` sao consultadas.
2. Filtro de Qdrant deve incluir `document_status = indexed` para chunks validos.
3. `rag_scope = []` retorna imediatamente `[]` sem chamar Qdrant.
4. `top_k` maximo: 20.

## Implementation Checklist

- [x] Adicionar `get_searchable_collections(tenant_id, collection_ids, allowed_statuses)` ao `CollectionRepository`.
- [x] Criar `rag/retriever.py` com `TenantRetriever(db, qdrant, embedder)`.
- [x] Implementar `retrieve(query, tenant_id, rag_scope, top_k)`.
- [x] Testar: scope vazio, nenhuma collection ready, resultado correto com mock Qdrant, isolamento cross-tenant.

## Acceptance Criteria

- [ ] `retrieve` com `rag_scope=[]` retorna `[]` sem chamar Qdrant.
- [ ] `retrieve` filtra apenas collections com `indexing_status` permitido.
- [ ] Chunks retornados tem `text`, `source` e `score`.
- [ ] Filtro Qdrant inclui `tenant_id` correto (isolamento cross-tenant).

## Verification

```bash
cd backend
pytest tests/test_stage_06_retriever.py
```

## Risks & Rollback

- **Risks**: vazamento cross-tenant se filtro de `tenant_id` for omitido no query Qdrant.
- **Rollback**: desabilitar RAG node retornando `retrieved_chunks = []` sem chamar retriever.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para retriever com RBAC e rag_scope.
- `[2026-05-09 00:00]`: Implementado TenantRetriever em rag/retriever.py, get_searchable_collections em CollectionRepository, search() em QdrantRagClient. 4 testes passando.
