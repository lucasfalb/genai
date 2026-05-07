# Task: TASK-043 - Documents Upload e Status API

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-043 |
| **Group** | RAG |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_06_rag.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Admins precisam fazer upload de documentos para uma collection e acompanhar o status de indexacao. Esta task expoe os endpoints de upload e status, persistindo o arquivo e enfileirando o job de indexacao sem bloquear a resposta.

## Objectives

- [ ] `POST /tenant/collections/{collection_id}/documents` — upload de arquivo (PDF/DOCX/TXT) ou URL.
- [ ] `GET /tenant/collections/{collection_id}/documents` — listar documents com status.
- [ ] `GET /tenant/collections/{collection_id}/documents/{document_id}` — detalhe com progresso.
- [ ] `DELETE /tenant/collections/{collection_id}/documents/{document_id}` — remover document e chunks do Qdrant.
- [ ] Ao criar document: `status = uploaded`, publicar job na fila Redis para o worker de indexacao.
- [ ] Adicionar requests Bruno em `genai-endpoints/TenantCollections/`.

## Non-Goals

- Execucao do pipeline de indexacao (TASK-044 — worker separado).
- Streaming de progresso via SSE.

## Stage Boundaries

Apenas persistencia de metadados e enfileiramento. O arquivo pode ser salvo em disco local ou storage configuravel.

## Dependencies

- TASK-042 (collections CRUD — document pertence a collection)

## Inputs & Contracts

- **Inputs**: arquivo multipart (`file`) ou `source_url` + `source_type`.
- **Outputs**: `DocumentResponse(id, collection_id, tenant_id, filename, source_type, status, chunk_count, error_message, created_at, indexed_at)`.
- **Schemas**: `DocumentResponse`, `ApiResponse[T]`.

## Constraints & Rules

1. Tipos aceitos: `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `text/plain`.
2. Tamanho maximo de arquivo: 50 MB (configuravel via settings).
3. `documents.status = uploaded` antes de enfileirar job.
4. `collections.indexing_status` atualizado para `indexing` ao receber primeiro documento.
5. Delete remove chunks do Qdrant pelo `document_id` no payload.

## Implementation Checklist

- [ ] Criar `DocumentResponse` schema em `app/schemas.py`.
- [ ] Adicionar endpoints de documents em `api/v1/tenant_collections.py` (ou router separado).
- [ ] Salvar arquivo em storage (disco local como primeiro passo) e registrar path no document.
- [ ] Publicar job `{"document_id": ..., "tenant_id": ..., "collection_id": ...}` em fila Redis `rag:indexing_queue`.
- [ ] Atualizar `collections.indexing_status` para `indexing` apos upload.
- [ ] Testar: upload PDF, list documents, get status, delete.

## Acceptance Criteria

- [ ] Upload retorna `DocumentResponse` com `status = uploaded`.
- [ ] Job publicado na fila Redis apos upload.
- [ ] `collections.indexing_status` muda para `indexing` apos primeiro upload.
- [ ] Delete de document inexistente retorna 404.

## Verification

```bash
cd backend
pytest tests/test_stage_06_documents.py
```

## Risks & Rollback

- **Risks**: arquivo grande pode saturar disco local; migrar para object storage em producao.
- **Rollback**: remover endpoints de documents e limpar fila Redis.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para upload e status de documents.
