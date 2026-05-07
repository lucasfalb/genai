# Task: TASK-002 - Tabelas Globais Core

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-002 |
| **Group** | CORE |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_01_core_db.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Esta task implementa as entidades globais que sustentam tenants, usuarios, associacoes, convites, catalogos globais e auditoria. Elas sao pre-requisito para isolamento por tenant e para os stages posteriores de Auth/RBAC, Registry e Engine.

## Objectives

- [x] Criar tabela `tenants`.
- [x] Criar tabela `users`.
- [x] Criar tabela `memberships`.
- [x] Criar tabela `invitations`, caso esteja definida na especificacao completa ou seja necessaria para o contrato de Stage 02.
- [x] Criar tabelas `llm_providers`, `skill_definitions` e `tool_definitions`, quando presentes no contrato canonico.
- [x] Criar tabela `audit_logs`.
- [x] Aplicar constraints de unicidade, chaves estrangeiras e defaults definidos no Stage 01.

## Non-Goals

- Implementar fluxos de login, convite ou reset de senha.
- Implementar UI de superadmin.
- Implementar execucao de skills/tools.

## Stage Boundaries

A task cria apenas estrutura e constraints relacionais. Regras de autorizacao e fluxos de autenticacao pertencem ao Stage 02.

## Dependencies

- TASK-001.

## Inputs & Contracts

- **Inputs**: schema SQL do Stage 01 e especificacao tecnica canonica.
- **Outputs**: migration com tabelas globais criadas.
- **Schemas**: `tenants`, `users`, `memberships`, `invitations`, `llm_providers`, `skill_definitions`, `tool_definitions`, `audit_logs`.

## Constraints & Rules

1. `tenants.slug` deve ser unico.
2. `users.email` deve ser unico.
3. `memberships` deve impedir associacao duplicada por `user_id` e `tenant_id`.
4. Catalogos globais nao devem depender de `tenant_id`.
5. `audit_logs` deve ser append-only no contrato da aplicacao.

## Implementation Checklist

- [x] Comparar tabelas globais em `stage_01_core_db.md` com `platform_technical_spec.md`.
- [x] Criar migration das tabelas globais.
- [x] Adicionar constraints e defaults.
- [x] Adicionar indices necessarios para lookup por slug/email.
- [x] Validar ordem de criacao por chaves estrangeiras.
- [x] Criar testes de migration ou introspeccao de schema.

## Acceptance Criteria

- [x] Todas as tabelas globais do Stage 01 existem no schema `public`.
- [x] Constraints de unicidade impedem duplicidade de slug, email e membership.
- [x] Chaves estrangeiras bloqueiam referencias invalidas.
- [x] Defaults de status, plan, settings e timestamps sao aplicados pelo banco.
- [x] Nao ha dependencia de `tenant_id` nas tabelas de catalogo global.

## Verification

```bash
# alembic upgrade head
# pytest tests/db
```

## Risks & Rollback

- **Risks**: divergencia entre stage resumido e especificacao canonica; criacao prematura de campos de Auth.
- **Rollback**: reverter migration das tabelas globais antes de aplicar stages dependentes.

## Execution Log

- `[2026-05-07 00:00]`: Task criada a partir do Stage 01.
- `[2026-05-07 12:20]`: Tabelas globais criadas na migration `20260507_0001`.
- `[2026-05-07 13:45]`: Checklists sincronizados com status COMPLETED.
