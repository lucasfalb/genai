# Task: TASK-014 - Ativacao de Skills e Tools por Instancia

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-014 |
| **Group** | REGISTRY |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_03_registry.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Instancias de agentes precisam ativar subconjuntos do catalogo global com configuracao tenant-scoped.

## Objectives

- [x] Criar endpoints tenant-scoped para ativar skill em instancia.
- [x] Criar endpoints tenant-scoped para ativar tool em instancia.
- [x] Validar que a instancia pertence ao tenant do contexto.
- [x] Invalidar cache de metadata apos alteracoes.

## Non-Goals

- Executar tools.
- Implementar handoff entre agentes.

## Stage Boundaries

Esta task se limita as tabelas `agent_instance_skills` e `agent_instance_tools`.

## Dependencies

- TASK-013

## Inputs & Contracts

- **Inputs**: `X-Tenant-ID`, instance id, skill/tool slug e config.
- **Outputs**: ativacao persistida por instancia.
- **Schemas**: `agent_instance_skills`, `agent_instance_tools`.

## Constraints & Rules

1. Endpoint deve exigir permissao `MANAGE_SKILLS_TOOLS`.
2. Tenant id deve vir do tenant context, nao do corpo do request.
3. Toda query tenant-scoped deve respeitar RLS.

## Implementation Checklist

- [x] Criar repositorio de ativacao.
- [x] Criar schemas de request/response.
- [x] Criar rotas tenant-scoped.
- [x] Adicionar testes de isolamento por tenant.

## Acceptance Criteria

- [x] Tenant admin ativa/desativa skill por instancia.
- [x] Tenant admin ativa/desativa tool por instancia.
- [x] Viewer nao consegue alterar ativacoes.
- [x] Instancia de outro tenant nao pode ser alterada.

## Verification

```bash
pytest
```

## Risks & Rollback

- **Risks**: ativacao sem validar tenant pode vazar capacidades entre tenants.
- **Rollback**: desabilitar ativacoes por instancia e invalidar cache Redis relacionado.

## Execution Log

- `[2026-05-07 13:00]`: Task criada a partir do Stage 03.
- `[2026-05-07 13:20]`: Rotas tenant-scoped de ativacao implementadas com RBAC e RLS.
- `[2026-05-07 13:35]`: Status ajustado para IN_PROGRESS; falta teste explicito de tentativa de alterar instancia de outro tenant.
- `[2026-05-07 14:05]`: Teste explicito de bloqueio cross-tenant adicionado e task concluida.
