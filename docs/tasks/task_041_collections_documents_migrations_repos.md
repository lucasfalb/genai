# Task: TASK-041 - Migracoes e Repositorios Collections e Documents

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-041 |
| **Group** | RAG |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_06_rag.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

O Stage 06 precisa das tabelas `collections` e `documents` no PostgreSQL para armazenar metadados de colecoes de documentos e controlar o status de indexacao. Esta task cria as migrations e os repositorios de acesso.

## Objectives

- [x] Criar migration Alembic para tabela `collections` com RLS tenant-scoped.
- [x] Criar migration Alembic para tabela `documents` com FK para `collections`.
- [x] Implementar `CollectionRepository` em `database/repositories/collections.py`.
- [x] Implementar `DocumentRepository` em `database/repositories/documents.py`.
- [x] Cobrir operacoes: create, list, get, update status/progress, delete (collection) e update status (document).

## Non-Goals

- Endpoints REST (TASK-042, TASK-043).
- Pipeline de indexacao (TASK-044).

## Stage Boundaries

Apenas banco de dados. Nenhum endpoint ou worker nesta task.

## Dependencies

- TASK-003 (tenant-scoped schema e RLS — padrao a seguir)

## Inputs & Contracts

- **Inputs**: `tenant_id`, nome/descricao de colecao, `filename`, `source_type`.
- **Outputs**: registros em `collections` e `documents`.
- **Schemas**: ver DDL em `docs/stages/stage_06_rag.md`.

## Constraints & Rules

1. `collections` tem RLS por `tenant_id` (USING e WITH CHECK).
2. `documents` herda isolamento via FK para `collections.tenant_id`.
3. `indexing_status` em `collections`: `empty | indexing | ready | partial | failed`.
4. `status` em `documents`: `uploaded | indexing | indexed | failed`.
5. `indexing_progress` em `collections`: FLOAT 0.0 a 1.0.

## Implementation Checklist

- [x] Criar `alembic/versions/XXXX_add_collections_documents.py`.
- [x] Habilitar RLS em `collections` com policy por `app.current_tenant_id`.
- [x] Criar `database/repositories/collections.py` com `CollectionRecord` e `CollectionRepository`.
- [x] Criar `database/repositories/documents.py` com `DocumentRecord` e `DocumentRepository`.
- [x] Testar: create collection, list por tenant, update indexing_status, create document, list por collection.

## Acceptance Criteria

- [x] `alembic upgrade head` cria `collections` e `documents` sem erros.
- [x] RLS impede leitura cross-tenant em `collections`.
- [x] `CollectionRepository` e `DocumentRepository` CRUD funcionais em testes.

## Verification

```bash
cd backend
alembic upgrade head
pytest tests/test_stage_06_repositories.py
```

## Risks & Rollback

- **Risks**: FK de `documents` para `collections` pode bloquear delete de collections com documents.
- **Rollback**: `alembic downgrade -1`.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para migrations e repositorios do Stage 06.
- `[2026-05-08 00:00]`: Implementada — migration 0011 idempotente (IF NOT EXISTS + DO $$ policy check), CollectionRepository (create/list/get/update_indexing_status/delete com explicit doc cleanup), DocumentRepository (create/list_by_collection/get/update_status), 12 testes (inclui cross-tenant RLS e cascade). 149 testes passando.
