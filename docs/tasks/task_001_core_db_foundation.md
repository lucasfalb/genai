# Task: TASK-001 - Core DB Foundation e Migrations

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-001 |
| **Group** | CORE |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_01_core_db.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Esta task cria a fundacao relacional da plataforma. O Stage 01 exige PostgreSQL como fonte de verdade, migrations versionadas e extensoes necessarias para UUIDs antes da criacao das tabelas de dominio.

## Objectives

- [x] Configurar conexao PostgreSQL para o backend.
- [x] Inicializar Alembic ou mecanismo equivalente de migrations.
- [x] Criar migration base com extensoes necessarias, incluindo `pgcrypto` para `gen_random_uuid()`.
- [x] Definir convencoes de nomes para constraints, indexes e migrations.
- [x] Documentar comandos locais para criar, aplicar e reverter migrations.

## Non-Goals

- Implementar autenticacao, JWT ou RBAC.
- Criar APIs administrativas.
- Implementar Redis, Qdrant ou LangGraph.

## Stage Boundaries

Esta implementacao deve se limitar ao dominio de banco relacional descrito no Stage 01. Qualquer dependencia de Auth/RBAC deve ser registrada como contrato futuro, sem implementar o Stage 02.

## Dependencies

- Nenhuma.

## Inputs & Contracts

- **Inputs**: variaveis de ambiente de conexao PostgreSQL.
- **Outputs**: estrutura de migrations executavel localmente e em CI.
- **Schemas**: migration inicial e configuracao de metadata SQL.

## Constraints & Rules

1. Migrations devem ser idempotentes no fluxo normal de upgrade/downgrade.
2. Nenhuma credencial de banco deve ser hardcoded.
3. Todos os objetos criados devem viver no schema `public`.
4. O banco deve suportar `UUID PRIMARY KEY DEFAULT gen_random_uuid()`.
5. O setup deve permitir execucao em ambiente local e CI.

## Implementation Checklist

- [x] Ler `docs/stages/stage_01_core_db.md` e confirmar limites de escopo.
- [x] Identificar framework ORM/query builder usado pelo projeto.
- [x] Configurar arquivo de conexao com PostgreSQL.
- [x] Inicializar Alembic ou ferramenta equivalente.
- [x] Criar migration base com extensoes.
- [x] Adicionar comandos de upgrade/downgrade em script ou documentacao.
- [x] Validar migration em banco limpo.
- [x] Validar downgrade quando aplicavel.

## Acceptance Criteria

- [x] Um banco PostgreSQL limpo recebe a migration base sem erro.
- [x] `gen_random_uuid()` funciona apos aplicar a migration.
- [x] O projeto possui comando documentado para aplicar migrations.
- [x] O projeto possui comando documentado para reverter a ultima migration.
- [x] Nao ha segredo ou string de conexao sensivel versionada.

## Verification

```bash
alembic upgrade head
alembic downgrade -1
pytest
```

## Risks & Rollback

- **Risks**: configuracao divergente entre local, CI e producao; migrations acopladas a ferramenta ainda nao escolhida.
- **Rollback**: reverter a migration base em ambiente nao produtivo ou recriar banco local.

## Execution Log

- `[2026-05-07 00:00]`: Task criada a partir do Stage 01.
- `[2026-05-07 12:20]`: Docker Compose, Alembic, migration base e testes minimos configurados.
- `[2026-05-07 12:40]`: Downgrade/upgrade da migration de grants validado.
