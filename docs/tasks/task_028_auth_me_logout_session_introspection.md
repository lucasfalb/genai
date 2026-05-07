# Task: TASK-028 - Auth Me Logout e Session Introspection

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-028 |
| **Group** | AUTH |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_05_base_multitenant_workflows.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Codex |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Clientes precisam descobrir o usuario autenticado, tenants acessiveis e encerrar sessoes revogando refresh token.

## Objectives

- [x] Criar endpoint `GET /auth/me`.
- [x] Criar endpoint `GET /auth/me/tenants`.
- [x] Criar endpoint `POST /auth/logout`.
- [x] Garantir resposta correta para superadmin sem memberships.

## Non-Goals

- Gerenciar todos os dispositivos do usuario.
- Implementar session dashboard.

## Stage Boundaries

Esta task complementa os endpoints de auth existentes sem alterar RBAC tenant-scoped.

## Dependencies

- TASK-008

## Inputs & Contracts

- **Inputs**: Bearer token e refresh token opcional para logout.
- **Outputs**: perfil do usuario, memberships ativas ou revogacao.
- **Schemas**: Pydantic responses de user/me e tenant access.

## Constraints & Rules

1. `me` nao deve retornar password hash.
2. `me/tenants` nao deve simular membership para superadmin.
3. Logout deve revogar refresh token informado quando presente.
4. Bruno deve ter requests autenticados para os endpoints.

## Implementation Checklist

- [x] Criar schemas de me/tenant access/logout.
- [x] Criar endpoints em auth.
- [x] Testar usuario pending, membro ativo e superadmin.
- [x] Atualizar Bruno e OpenAPI.

## Acceptance Criteria

- [x] `GET /auth/me` retorna identidade global segura.
- [x] `GET /auth/me/tenants` retorna memberships reais.
- [x] Superadmin retorna `is_superadmin=true` e memberships vazias.
- [x] Logout revoga refresh token informado.

## Verification

```bash
cd backend
pytest tests/test_stage_05_auth_introspection.py
```

## Risks & Rollback

- **Risks**: introspeccao pode vazar dados globais indevidos.
- **Rollback**: remover endpoints de introspeccao ate revisar payloads.

## Execution Log

- `[2026-05-07 15:40]`: Task criada para cobrir perfil autenticado e logout.
- `[2026-05-07 18:25]`: Implementacao iniciada para `me`, `me/tenants` e `logout`.
- `[2026-05-07 18:40]`: Endpoints de introspeccao e logout implementados com Bruno, OpenAPI e testes de integracao.
