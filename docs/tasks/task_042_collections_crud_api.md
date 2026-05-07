# Task: TASK-042 - Collections CRUD API Tenant-Scoped

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-042 |
| **Group** | RAG |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_06_rag.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Tenant admins precisam criar, listar, atualizar e remover colecoes de documentos que alimentam o RAG das instancias. Esta task expoe o CRUD tenant-scoped de `collections` com RBAC e registro de audit/version.

## Objectives

- [ ] Criar `APIRouter` em `api/v1/tenant_collections.py` com prefix `/tenant/collections`.
- [ ] `GET /tenant/collections` — listar collections do tenant.
- [ ] `POST /tenant/collections` — criar collection (status inicial `empty`).
- [ ] `GET /tenant/collections/{collection_id}` — detalhe.
- [ ] `PATCH /tenant/collections/{collection_id}` — atualizar nome/descricao.
- [ ] `DELETE /tenant/collections/{collection_id}` — remover se sem documents indexados.
- [ ] Registrar audit/version via `record_tenant_mutation`.
- [ ] Adicionar requests Bruno em `genai-endpoints/TenantCollections/`.

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

- [ ] Criar schemas `CollectionCreateRequest`, `CollectionUpdateRequest`, `CollectionResponse` em `app/schemas.py`.
- [ ] Criar `api/v1/tenant_collections.py` com 5 endpoints.
- [ ] Registrar router em `app/main.py`.
- [ ] Adicionar 5 arquivos `.bru` em `genai-endpoints/TenantCollections/`.
- [ ] Testar: create, list, get, update, delete bloqueado com documents indexados.

## Acceptance Criteria

- [ ] CRUD completo de collections retorna `ApiResponse[CollectionResponse]`.
- [ ] Delete com documents indexados retorna 409.
- [ ] Audit log gerado em create, update e delete.
- [ ] Viewer recebe 403 em mutacoes.

## Verification

```bash
cd backend
pytest tests/test_stage_06_collections.py
```

## Risks & Rollback

- **Rollback**: remover router de `app/main.py` e desregistrar endpoints.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para CRUD de collections tenant-scoped.
