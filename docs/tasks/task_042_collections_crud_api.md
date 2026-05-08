# Task: TASK-042 - Collections CRUD API Tenant-Scoped

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-042 |
| **Group** | RAG |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_06_rag.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Tenant admins precisam criar, listar, atualizar e remover colecoes de documentos que alimentam o RAG das instancias. Esta task expoe o CRUD tenant-scoped de `collections` com RBAC e registro de audit/version.

## Objectives

- [x] Criar `APIRouter` em `api/v1/tenant_collections.py` com prefix `/tenant/collections`.
- [x] `GET /tenant/collections` — listar collections do tenant.
- [x] `POST /tenant/collections` — criar collection (status inicial `empty`).
- [x] `GET /tenant/collections/{collection_id}` — detalhe.
- [x] `PATCH /tenant/collections/{collection_id}` — atualizar nome/descricao.
- [x] `DELETE /tenant/collections/{collection_id}` — remover se sem documents indexados.
- [x] Registrar audit/version via `record_tenant_mutation`.
- [x] Adicionar requests Bruno em `genai-endpoints/TenantCollections/`.

## Non-Goals

- Upload de documentos (TASK-043).
- Associacao de collection a instancia via `rag_scope` (TASK-032 ja suporta, nao precisa de novo endpoint).

## Stage Boundaries

Apenas CRUD de collections. Nao toca pipeline de indexacao.

## Dependencies

- TASK-041 (repositorios de collections)
- TASK-030 (RBAC membership — padrao de autenticacao tenant-scoped)

## Inputs & Contracts

- **Inputs**: `name` (required), `description` (optional).
- **Outputs**: `CollectionResponse(id, tenant_id, name, description, indexing_status, indexing_progress, document_count, indexed_count, failed_count, last_indexed_at, created_at)`.
- **Schemas**: `CollectionCreateRequest`, `CollectionUpdateRequest`, `CollectionResponse`, `ApiResponse[T]`.

## Constraints & Rules

1. Requer Bearer token, `X-Tenant-ID` e permissao `MANAGE_AGENT_INSTANCES`.
2. Delete bloqueado se collection tiver documents com `status = indexed`.
3. Toda mutacao gera audit log com `resource = 'collections'`.
4. RLS via `set_config('app.current_tenant_id', ...)` antes de qualquer query.

## Implementation Checklist

- [x] Criar schemas `CollectionCreateRequest`, `CollectionUpdateRequest`, `CollectionResponse` em `app/schemas.py`.
- [x] Criar `api/v1/tenant_collections.py` com 5 endpoints.
- [x] Registrar router em `app/main.py`.
- [x] Adicionar 5 arquivos `.bru` em `genai-endpoints/TenantCollections/`.
- [x] Testar: create, list, get, update, delete bloqueado com documents indexados.

## Acceptance Criteria

- [x] CRUD completo de collections retorna `ApiResponse[CollectionResponse]`.
- [x] Delete com documents indexados retorna 409.
- [x] Audit log gerado em create, update e delete.
- [x] Viewer recebe 403 em mutacoes.

## Verification

```bash
cd backend
pytest tests/test_stage_06_collections.py
```

## Risks & Rollback

- **Rollback**: remover router de `app/main.py` e desregistrar endpoints.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para CRUD de collections tenant-scoped.
- `[2026-05-08 00:00]`: Implementada — 3 schemas (CollectionCreate/Update/Response), CollectionRepository.update_metadata(), router 5 endpoints com RLS + audit (create/update/delete), delete 409 bloqueado por indexed_count, 5 Bruno files, 10 testes (inclui viewer 403, cross-tenant 404, audit log 3 entries). 159 testes passando.
