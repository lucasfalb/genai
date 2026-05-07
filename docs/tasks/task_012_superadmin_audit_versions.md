# Task: TASK-012 - Auditoria e Versoes para Acoes de Superadmin

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-012 |
| **Group** | AUTH |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_02_auth_rbac.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Esta task formaliza a diferenca entre membership visivel e autoria de mudancas feitas pelo superadmin em escopo de tenant.

## Objectives

- [x] Registrar `actor_type` e `actor_role` em `audit_logs`.
- [x] Criar tabela tenant-scoped `resource_versions`.
- [x] Persistir mutacoes versionaveis com `tenant_id`, `changed_by` e contexto de ator.
- [x] Garantir que superadmin apareca em auditoria e versoes, mas nao em members.

## Non-Goals

- Criar UI de historico de versoes.
- Versionar todos os recursos da plataforma nesta etapa.

## Stage Boundaries

Esta task pertence ao Stage 02 e amplia o contrato de auditoria criado no Stage 01 sem transformar superadmin em membro de tenant.

## Dependencies

- TASK-005
- TASK-011

## Inputs & Contracts

- **Inputs**: mutacoes tenant-scoped executadas por usuario comum ou superadmin.
- **Outputs**: entradas em `audit_logs` e, quando aplicavel, `resource_versions`.
- **Schemas**: colunas de ator em `audit_logs` e tabela `resource_versions`.

## Constraints & Rules

1. Membership define pertencimento visivel ao tenant.
2. Audit e versions registram autoria de mudancas, inclusive de superadmin.
3. Dados sensiveis devem ser redigidos antes de persistir snapshots ou metadata.
4. `resource_versions` deve respeitar isolamento por tenant.

## Implementation Checklist

- [x] Criar migration de ator em audit logs.
- [x] Criar migration de `resource_versions` com RLS.
- [x] Atualizar repositorios de auditoria e versoes.
- [x] Testar superadmin fora de members e presente em logs/versionamento.

## Acceptance Criteria

- [x] Acao de superadmin em tenant grava audit log com `actor_type = 'superadmin'`.
- [x] Mutacao versionavel de superadmin grava `resource_versions` com tenant correto.
- [x] Listagem de membros nao retorna superadmin.
- [x] Snapshots e metadata passam por redacao de campos sensiveis.

## Verification

```bash
pytest
```

## Risks & Rollback

- **Risks**: omitir ator global em auditoria dificulta rastreabilidade operacional.
- **Rollback**: manter colunas novas nulas apenas em ambiente nao produtivo ou reverter migration se nenhuma mutacao depender dela.

## Execution Log

- `[2026-05-07 12:45]`: Auditoria e versionamento para acoes de superadmin implementados e documentados.
