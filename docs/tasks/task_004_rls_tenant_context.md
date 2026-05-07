# Task: TASK-004 - RLS e TenantContext no Banco

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-004 |
| **Group** | SECURITY |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_01_core_db.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

O Stage 01 define isolamento por `tenant_id` como regra primaria e RLS como segunda camada de defesa. Esta task cria as policies e o contrato de injecao do tenant ativo na sessao PostgreSQL.

## Objectives

- [x] Habilitar RLS em todas as tabelas tenant-scoped.
- [x] Definir policy padrao baseada em setting de sessao, por exemplo `app.current_tenant_id`.
- [x] Garantir que queries tenant-scoped falhem ou retornem vazio sem tenant ativo.
- [x] Criar helper de conexao/transacao para setar tenant ativo antes de executar queries.
- [x] Cobrir isolamento cross-tenant com testes automatizados.

## Non-Goals

- Implementar autorizacao por role de usuario.
- Implementar middleware HTTP completo do Stage 02.
- Implementar endpoints de negocio.

## Stage Boundaries

A task trata apenas isolamento de dados no banco e contrato tecnico do tenant ativo. Validacao de membership, roles e permissoes pertence ao Stage 02.

## Dependencies

- TASK-001.
- TASK-003.

## Inputs & Contracts

- **Inputs**: `tenant_id` resolvido pelo backend em stages posteriores.
- **Outputs**: policies RLS e helper de aplicacao de tenant na conexao.
- **Schemas**: policies PostgreSQL para tabelas tenant-scoped.

## Constraints & Rules

1. Todas as tabelas tenant-scoped devem ter RLS habilitado.
2. Policies devem filtrar por `tenant_id`.
3. O tenant ativo deve ser configurado por transacao ou por escopo de conexao controlado.
4. A conexao nao pode vazar tenant ativo entre requests.
5. Tabelas globais devem permanecer acessiveis apenas conforme contratos de stages posteriores.

## Implementation Checklist

- [x] Inventariar tabelas tenant-scoped.
- [x] Criar migration de `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`.
- [x] Criar policies de `SELECT`, `INSERT`, `UPDATE` e `DELETE` quando aplicavel.
- [x] Implementar helper de contexto para setar `app.current_tenant_id`.
- [x] Garantir reset/escopo correto ao devolver conexao ao pool.
- [x] Criar testes com dois tenants e dados cruzados.
- [x] Testar operacoes sem tenant ativo.

## Acceptance Criteria

- [x] Usuario com tenant A nao le registros do tenant B em nenhuma tabela tenant-scoped.
- [x] Inserts tenant-scoped exigem `tenant_id` igual ao tenant ativo.
- [x] Updates e deletes nao afetam registros de outro tenant.
- [x] Testes comprovam que ausencia de tenant ativo nao retorna dados tenant-scoped.
- [x] Todas as policies estao versionadas em migration.

## Verification

```bash
# pytest tests/db/test_rls_isolation.py
```

## Risks & Rollback

- **Risks**: vazamento de contexto em pool de conexoes; policies permissivas demais; bloqueio acidental de migrations ou jobs administrativos.
- **Rollback**: desabilitar RLS temporariamente apenas em ambiente controlado e corrigir policies antes de liberar acesso multi-tenant.

## Execution Log

- `[2026-05-07 00:00]`: Task criada a partir do Stage 01.
- `[2026-05-07 12:20]`: RLS habilitado com policies por `app.current_tenant_id` e usuario `genai_app` sem `BYPASSRLS`.
- `[2026-05-07 13:45]`: Checklists sincronizados com status COMPLETED.
