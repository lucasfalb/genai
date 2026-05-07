# Task: TASK-016 - Credenciais Tenant-Scoped e Vault Refs

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-016 |
| **Group** | SECURITY |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_03_registry.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Skills que exigem credencial devem guardar somente referencia segura para cofre externo, evitando segredo em claro no banco ou logs.

## Objectives

- [x] Criar repositorio de `tool_credentials`.
- [x] Validar `secret_ref` e metadata nao sensivel.
- [x] Criar endpoints tenant-scoped de credenciais.
- [x] Redigir campos sensiveis em respostas e logs.

## Non-Goals

- Integrar HashiCorp Vault ou AWS Secrets Manager real.
- Descriptografar segredo para execucao.

## Stage Boundaries

Esta task cobre persistencia de referencias de credencial no Stage 03.

## Dependencies

- TASK-013

## Inputs & Contracts

- **Inputs**: skill slug, `secret_ref` e metadata nao sensivel.
- **Outputs**: credential id e referencia mascarada.
- **Schemas**: `tool_credentials.credential_data`.

## Constraints & Rules

1. Valores como token, api_key, password e secret nao podem ser aceitos em claro.
2. Respostas nao devem retornar segredo.
3. Endpoint deve exigir `MANAGE_SKILLS_TOOLS`.

## Implementation Checklist

- [x] Criar validacao contra campos sensiveis.
- [x] Criar repositorio de credenciais.
- [x] Criar rotas tenant-scoped.
- [x] Adicionar testes de rejeicao de segredo em claro.

## Acceptance Criteria

- [x] Tenant admin salva referencia de credencial por skill.
- [x] Payload com segredo em claro e rejeitado.
- [x] Resposta retorna somente metadata segura.
- [x] Viewer nao gerencia credenciais.

## Verification

```bash
pytest
```

## Risks & Rollback

- **Risks**: aceitar segredo em claro pode vazar credenciais em banco, logs ou backups.
- **Rollback**: apagar registros inseguros e rotacionar credenciais afetadas.

## Execution Log

- `[2026-05-07 13:00]`: Task criada a partir do Stage 03.
- `[2026-05-07 13:20]`: Credenciais por `secret_ref` implementadas sem armazenar segredo em claro.
