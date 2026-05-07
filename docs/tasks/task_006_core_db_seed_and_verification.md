# Task: TASK-006 - Seeds e Verificacao do Core DB

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-006 |
| **Group** | CORE |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_01_core_db.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Depois das migrations e policies, o Stage 01 precisa de uma verificacao reproduzivel. Esta task cria dados minimos e testes para comprovar schema, constraints, RLS e contratos basicos antes de avancar para Auth/RBAC.

## Objectives

- [x] Criar seed minimo com dois tenants, usuarios e memberships.
- [x] Criar dados tenant-scoped para agent instances.
- [x] Validar que migrations sobem do zero localmente.
- [x] Validar RLS com dados de tenants diferentes.
- [x] Validar constraints e indices criticos.
- [x] Documentar checklist de conclusao do Stage 01.

## Non-Goals

- Criar massa real de demo para produto.
- Criar seeds de skills/tools completas para producao.
- Implementar testes end-to-end de frontend.

## Stage Boundaries

A task valida somente o Stage 01. Testes de login, permissoes por role, prompt runtime, RAG e canais pertencem aos stages posteriores.

## Dependencies

- TASK-001.
- TASK-002.
- TASK-003.
- TASK-004.
- TASK-005.

## Inputs & Contracts

- **Inputs**: migrations aplicadas e configuracao PostgreSQL de teste.
- **Outputs**: seed minimo, suite de testes de banco e checklist de aceite do Stage 01.
- **Schemas**: todos os schemas criados no Stage 01.

## Constraints & Rules

1. Seeds devem ser deterministicos e seguros para ambiente local/teste.
2. Seeds nao devem conter credenciais reais.
3. Testes devem criar ou limpar seus proprios dados.
4. O checklist deve referenciar os comandos reais do projeto.
5. Falhas de RLS devem bloquear conclusao do Stage 01.

## Implementation Checklist

- [x] Criar fixture ou script de seed minimo.
- [x] Criar testes de subida de migrations.
- [x] Criar testes de constraints globais.
- [x] Criar testes de constraints tenant-scoped.
- [x] Criar testes de RLS cross-tenant.
- [x] Criar testes basicos de sessoes/mensagens.
- [x] Documentar comandos de verificacao.

## Acceptance Criteria

- [x] Banco limpo aplica todas as migrations do Stage 01 sem erro.
- [x] Suite de testes de banco passa localmente.
- [x] Cross-tenant read/write e bloqueado ou filtrado por RLS.
- [x] Seeds criam dados minimos para dois tenants sem conflito.
- [x] Checklist final do Stage 01 esta documentado.

## Verification

```bash
alembic upgrade head
python scripts/seed_stage_01.py
pytest
```

## Risks & Rollback

- **Risks**: testes dependentes de ordem; seeds com dados irreais que mascaram constraints; CI sem PostgreSQL compativel.
- **Rollback**: remover seed/teste problematico e manter migrations bloqueadas ate a verificacao essencial passar.

## Execution Log

- `[2026-05-07 00:00]`: Task criada a partir do Stage 01.
- `[2026-05-07 12:20]`: Suite inicial de testes criada para schema, constraints, RLS e sequenciamento unico por sessao.
- `[2026-05-07 12:35]`: Seed minimo criado e suite completa validada com 8 testes passando.
