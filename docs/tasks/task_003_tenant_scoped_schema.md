# Task: TASK-003 - Schema Tenant-Scoped Completo

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-003 |
| **Group** | CORE |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_01_core_db.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Esta task cria todas as tabelas tenant-scoped do Stage 01. Mesmo que algumas sejam usadas por stages futuros, o Stage 01 mantem o schema completo para evitar divergencia entre dominios.

## Objectives

- [x] Criar `agent_instances`.
- [x] Criar `agent_instance_skills`.
- [x] Criar `agent_instance_tools`.
- [x] Criar `agent_links`.
- [x] Criar `tool_credentials`.
- [x] Criar `collections`.
- [x] Criar `documents`.
- [x] Criar `document_permissions`, se confirmada na especificacao canonica.
- [x] Criar `agent_channel_configs`.
- [x] Criar indices tenant-scoped definidos no Stage 01.

## Non-Goals

- Implementar CRUD de instancias, canais, RAG ou hand-off.
- Implementar criptografia real de credenciais.
- Implementar integracao com Qdrant.

## Stage Boundaries

A task entrega somente estrutura relacional, constraints e indices. Logica de Registry, Engine, RAG, Hand-off e Channels fica nos stages posteriores.

## Dependencies

- TASK-001.
- TASK-002.

## Inputs & Contracts

- **Inputs**: definicao SQL tenant-scoped do Stage 01.
- **Outputs**: migration com tabelas tenant-scoped completas.
- **Schemas**: tabelas com `tenant_id` obrigatorio e FKs para entidades globais ou tenant-scoped.

## Constraints & Rules

1. Toda tabela tenant-scoped deve possuir `tenant_id UUID NOT NULL`.
2. FKs devem preservar integridade entre instancia, skill, tool, colecao, documento, sessao e canal.
3. Constraints `UNIQUE` devem seguir o Stage 01.
4. Campos JSONB devem ter default seguro (`{}` ou `[]`) conforme contrato.
5. Indices devem favorecer consultas por `tenant_id`, `instance_id`, status e ordenacao temporal.

## Implementation Checklist

- [x] Listar todas as tabelas tenant-scoped do Stage 01.
- [x] Confirmar campos que existem na especificacao canonica mas nao aparecem no resumo.
- [x] Criar migration em ordem compativel com FKs.
- [x] Aplicar constraints `UNIQUE`.
- [x] Criar indices definidos no Stage 01.
- [x] Validar defaults JSONB e timestamps.
- [x] Criar testes de integridade referencial.

## Acceptance Criteria

- [x] Todas as tabelas tenant-scoped existem com `tenant_id NOT NULL`.
- [x] Registros sem tenant sao rejeitados pelo banco.
- [x] FKs impedem vinculos com entidades inexistentes.
- [x] Indices do Stage 01 existem com os nomes esperados ou equivalentes.
- [x] Campos JSONB recebem defaults corretos.

## Verification

```bash
# alembic upgrade head
# pytest tests/db/test_tenant_scoped_schema.py
```

## Risks & Rollback

- **Risks**: criar tabelas futuras com contrato incompleto; inconsistencias de tenant entre tabelas relacionadas.
- **Rollback**: reverter migration tenant-scoped antes de popular dados de teste ou seeds.

## Execution Log

- `[2026-05-07 00:00]`: Task criada a partir do Stage 01.
- `[2026-05-07 12:20]`: Schema tenant-scoped completo criado com indices e constraints principais.
- `[2026-05-07 13:45]`: Checklists sincronizados com status COMPLETED.
