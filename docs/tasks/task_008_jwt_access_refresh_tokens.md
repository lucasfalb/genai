# Task: TASK-008 - JWT Access e Refresh Tokens

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-008 |
| **Group** | AUTH |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_02_auth_rbac.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Esta task adiciona sessao autenticada stateless por access token e rotacao persistida de refresh tokens.

## Objectives

- [x] Gerar JWT de access token com `sub` e expiracao.
- [x] Gerar refresh token opaco e armazenar somente hash.
- [x] Implementar endpoint de refresh com rotacao.
- [x] Revogar refresh token consumido.

## Non-Goals

- Implementar MFA.
- Implementar device management.

## Stage Boundaries

Esta task pertence ao Stage 02 e apenas consome usuarios e memberships existentes.

## Dependencies

- TASK-007

## Inputs & Contracts

- **Inputs**: credenciais validas e refresh token opaco.
- **Outputs**: access token JWT, refresh token rotacionado e metadados de membership quando aplicavel.
- **Schemas**: tabela `refresh_tokens` e payloads de auth.

## Constraints & Rules

1. Refresh token deve ser armazenado como hash.
2. Token expirado ou revogado deve ser rejeitado.
3. JWT deve usar segredo e algoritmo configuraveis via `.env`.

## Implementation Checklist

- [x] Criar migration de refresh tokens.
- [x] Implementar emissao de access e refresh tokens.
- [x] Implementar rotacao no endpoint `/auth/refresh`.
- [x] Testar consumo unico de refresh token.

## Acceptance Criteria

- [x] Login autenticado emite access e refresh tokens.
- [x] Refresh valido retorna novo par de tokens.
- [x] Refresh token antigo deixa de ser aceito apos rotacao.
- [x] Tokens respeitam expiracao configurada.

## Verification

```bash
pytest
```

## Risks & Rollback

- **Risks**: reutilizacao indevida de refresh token se a revogacao falhar.
- **Rollback**: revogar tokens persistidos e reverter endpoint de refresh em ambiente nao produtivo.

## Execution Log

- `[2026-05-07 12:30]`: JWT, refresh token e testes de rotacao implementados.
