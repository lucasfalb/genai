# Task: TASK-011 - Superadmin Global e Templates de Email

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-011 |
| **Group** | AUTH |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_02_auth_rbac.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Esta task cria a regra de superadmin global e move comunicacoes transacionais para templates gerenciaveis no banco.

## Objectives

- [x] Definir `users.is_superadmin` como responsavel global da plataforma.
- [x] Permitir superadmin acessar qualquer tenant sem membership visivel.
- [x] Criar tabela global `email_templates`.
- [x] Seedar templates de ativacao, convite, recuperacao de senha e comunicacoes relacionadas.
- [x] Criar endpoints de gerenciamento para superadmin.

## Non-Goals

- Enviar emails por provider externo.
- Criar frontend administrativo.

## Stage Boundaries

Esta task pertence ao Stage 02 e documenta contrato para areas administrativas futuras.

## Dependencies

- TASK-008
- TASK-010

## Inputs & Contracts

- **Inputs**: usuario autenticado com `is_superadmin = true` e payloads de template.
- **Outputs**: templates globais consultaveis e atualizaveis por superadmin.
- **Schemas**: `users.is_superadmin` e tabela `email_templates`.

## Constraints & Rules

1. Superadmin tem controle global, mas nao deve aparecer em listagens de membros de tenant.
2. Templates de email devem ficar no banco e ser gerenciaveis pelo superadmin.
3. Usuario comum nao pode acessar endpoints de superadmin.

## Implementation Checklist

- [x] Adicionar suporte a role `superadmin`.
- [x] Ajustar tenant context para superadmin sem membership.
- [x] Criar migration e seeds de `email_templates`.
- [x] Criar endpoints de listagem, detalhe e atualizacao de templates.
- [x] Testar exclusao do superadmin em listagem de membros.

## Acceptance Criteria

- [x] Superadmin autentica sem membership ativo.
- [x] Superadmin tem permissao total por tenant.
- [x] Superadmin nao aparece em `get tenant members`.
- [x] Templates padrao existem no banco e podem ser gerenciados.

## Verification

```bash
pytest
```

## Risks & Rollback

- **Risks**: misturar superadmin com membership real pode expor usuario global como membro de tenant.
- **Rollback**: remover memberships indevidos e manter controle via `users.is_superadmin`.

## Execution Log

- `[2026-05-07 12:40]`: Superadmin global e templates de email implementados.
