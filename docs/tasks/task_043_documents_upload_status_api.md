# Task: TASK-043 - Documents Upload e Status API

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-043 |
| **Group** | RAG |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_06_rag.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-09 |

## Context

Admins precisam fazer upload de documentos para uma collection e acompanhar o status de indexacao. Esta task expoe os endpoints de upload e status, persistindo o arquivo em object storage S3-compatible e enfileirando o job de indexacao sem bloquear a resposta.

## Objectives

- [x] `POST /tenant/collections/{collection_id}/documents` - upload de arquivo (PDF/DOCX/TXT/MD) para S3-compatible storage.
- [x] `GET /tenant/collections/{collection_id}/documents` - listar documents com status.
- [x] `GET /tenant/collections/{collection_id}/documents/{document_id}` - detalhe com progresso.
- [x] `DELETE /tenant/collections/{collection_id}/documents/{document_id}` - remover document, objeto armazenado e enfileirar remocao de chunks.
- [x] `POST /tenant/collections/{collection_id}/reindex` - resetar status dos documents e enfileirar nova indexacao da collection.
- [x] Ao criar document: `status = uploaded`, publicar job na fila Redis para o worker de indexacao.
- [x] Adicionar requests Bruno em `genai-endpoints/TenantCollections/`.
- [x] Validar endpoint contracts via OpenAPI apos consolidacao das respostas documentadas.

## Non-Goals

- Execucao do pipeline de indexacao (TASK-044 - worker separado).
- Streaming de progresso via SSE.

## Stage Boundaries

Apenas persistencia de metadados, object storage S3-compatible e enfileiramento. O arquivo original nao deve ser salvo em filesystem local nem no Qdrant.

## Dependencies

- TASK-042 (collections CRUD - document pertence a collection)

## Inputs & Contracts

- **Inputs**: arquivo multipart (`file`) ou `source_url` + `source_type`.
- **Outputs**: `DocumentResponse(id, collection_id, tenant_id, filename, source_type, status, chunk_count, error_message, content_type, size_bytes, created_at, indexed_at)`.
- **Schemas**: `DocumentResponse`, `ApiResponse[T]`.
- **Reindex**: `POST /tenant/collections/{collection_id}/reindex` retorna `CollectionResponse` e publica jobs na fila Redis para todos os documents da collection.

## Constraints & Rules

1. Tipos aceitos: `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `text/plain`, `text/markdown`.
2. Tamanho maximo de arquivo: 50 MB (configuravel via settings).
3. `documents.status = uploaded` antes de enfileirar job.
4. `collections.indexing_status` atualizado para `indexing` ao receber primeiro documento.
5. Delete remove chunks do Qdrant pelo `document_id` no payload.
6. Qdrant armazena embeddings e payload JSON de chunks; arquivos originais ficam em S3-compatible storage.
7. Ambiente local deve subir MinIO via `docker-compose.yml`.

## Implementation Checklist

- [x] Criar `DocumentResponse` schema em `app/schemas.py`.
- [x] Adicionar endpoints de documents em `api/v1/tenant_collections.py` (ou router separado).
- [x] Salvar arquivo em S3-compatible object storage e registrar `storage_bucket`/`storage_key` no document.
- [x] Instanciar MinIO no ambiente local via `docker-compose.yml`.
- [x] Publicar job `{"document_id": ..., "tenant_id": ..., "collection_id": ...}` em fila Redis `rag:indexing_queue`.
- [x] Atualizar `collections.indexing_status` para `indexing` apos upload.
- [x] Adicionar endpoint e Bruno request de reindex para collection inteira.
- [x] Testar: upload PDF, list documents, get status, delete.
- [x] Validar OpenAPI e Bruno contra o padrao de endpoints.

## Acceptance Criteria

- [x] Upload retorna `DocumentResponse` com `status = uploaded`.
- [x] Job publicado na fila Redis apos upload.
- [x] `collections.indexing_status` muda para `indexing` apos primeiro upload.
- [x] Delete de document inexistente retorna 404.
- [x] Reindex de collection enfileira um job por document e reseta status para `uploaded`.
- [x] Resposta publica nao expoe path local nem chave interna do object storage.
- [x] `scripts/validate_openapi.py` passa com os endpoints de documents.

## Verification

```bash
cd backend
pytest tests/test_stage_06_documents.py
cd ..
backend\.venv\Scripts\python scripts\validate_openapi.py
python scripts/validate_tasks.py
```

## Risks & Rollback

- **Risks**: indisponibilidade do object storage bloqueia upload; objeto pode ficar orfao se houver falha entre upload e insert, mitigado por delete compensatorio.
- **Rollback**: remover endpoints de documents e limpar fila Redis.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para upload e status de documents.
- `[2026-05-09 00:00]`: Corrigido contrato para object storage S3-compatible; Qdrant fica restrito a vetores/payload JSON de chunks e MinIO passa a ser o backend local.
- `[2026-05-09 00:00]`: Endpoint contract validado com `scripts/validate_openapi.py`; Bruno cobre upload/list/get/delete de documents.
- `[2026-05-09 00:00]`: Adicionado `POST /tenant/collections/{collection_id}/reindex` com Bruno e cobertura de teste.
