# Stage 06 Tasks - RAG, Knowledge Base e Retrieval

| ID | Task | Status | Priority | Depends On |
| :--- | :--- | :--- | :--- | :--- |
| TASK-041 | [Migracoes e Repositorios Collections e Documents](task_041_collections_documents_migrations_repos.md) | COMPLETED | CRITICAL | TASK-003 |
| TASK-042 | [Collections CRUD API Tenant-Scoped](task_042_collections_crud_api.md) | COMPLETED | CRITICAL | TASK-041, TASK-030 |
| TASK-043 | [Documents Upload e Status API](task_043_documents_upload_status_api.md) | COMPLETED | HIGH | TASK-042 |
| TASK-044 | [Indexing Pipeline Worker](task_044_indexing_pipeline_worker.md) | COMPLETED | CRITICAL | TASK-043 |
| TASK-045 | [TenantRetriever com RBAC e rag_scope](task_045_tenant_retriever_rbac_rag_scope.md) | COMPLETED | CRITICAL | TASK-041, TASK-015 |
| TASK-046 | [RAG Node Integration no LangGraph](task_046_rag_node_langgraph_integration.md) | COMPLETED | HIGH | TASK-045, TASK-039 |
| TASK-047 | [Verificacao Stage 06 RAG](task_047_stage_06_rag_verification.md) | COMPLETED | HIGH | TASK-041, TASK-042, TASK-043, TASK-044, TASK-045, TASK-046 |
| TASK-084 | [Migrar Indexacao RAG para Backend Gerenciado](task_084_migrar_indexacao_rag_backend_gerenciado.md) | IN_PROGRESS | HIGH | TASK-043, TASK-044, TASK-047 |

## Scope

Estas tasks cobrem o Stage 06 definido em `docs/stages/stage_06_rag.md`: tabelas `collections` e `documents`, pipeline de indexacao com Qdrant, retriever com RBAC por `rag_scope` e integracao do RAG node no grafo LangGraph.

## Implementation Order

1. Migrations e repositorios de collections/documents.
2. CRUD tenant-scoped de collections.
3. Upload e status de documents.
4. Worker de indexacao background (chunking, embedding, Qdrant).
5. Retriever com RBAC filtrando por `rag_scope` e `indexing_status`.
6. Integrar RAG node real no grafo.
7. Verificacao end-to-end.

## Notes

- Qdrant compartilhado por tenant/plan; filtros por `tenant_id` e `collection_id` no payload.
- Qdrant armazena vetores e payload JSON de chunks; arquivos originais devem ficar em object storage S3-compatible.
- Ambiente local usa MinIO como backend S3-compatible.
- `rag_scope` da instancia define quais collections podem ser consultadas.
- Pipeline de indexacao e assincrono — nao bloqueia resposta ao upload.
- Toda rota nova deve ganhar request Bruno em `genai-endpoints/`.
- Toda rota JSON usa envelope `ApiResponse[T]`.
