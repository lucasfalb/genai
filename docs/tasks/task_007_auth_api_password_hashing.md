# Task: TASK-007 - Auth API e Password Hashing

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-007 |
| **Group** | AUTH |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_02_auth_rbac.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Esta task cria a API inicial de autenticacao para registrar usuarios e validar credenciais sem armazenar senhas em texto puro.

## Objectives

- [x] Implementar registro de usuario com email normalizado.
- [x] Persistir `password_hash` usando Argon2.
- [x] Implementar login por email e senha.
- [x] Retornar estado `awaiting_assignment` quando usuario comum ainda nao possuir membership ativo.

## Non-Goals

- Implementar envio real de email.
- Implementar frontend de login.

## Stage Boundaries

Esta task se limita ao Stage 02 e depende das tabelas globais criadas no Stage 01.

## Dependencies

- TASK-001
- TASK-002

## Inputs & Contracts

- **Inputs**: payloads de registro e login.
- **Outputs**: usuario pendente no registro e resultado autenticado ou aguardando assignment no login.
- **Schemas**: modelos Pydantic de auth e tabela `users`.

## Constraints & Rules

1. Senhas nunca devem ser logadas ou retornadas em resposta.
2. Hash de senha deve usar algoritmo resistente a brute force.
3. Email deve ser tratado como identificador unico e case-insensitive na pratica.

## Implementation Checklist

- [x] Criar utilitario de hash e verificacao de senha.
- [x] Criar endpoints de registro e login.
- [x] Validar payloads com Pydantic.
- [x] Cobrir casos de credencial invalida.

## Acceptance Criteria

- [x] Registro cria usuario pendente com hash de senha.
- [x] Login valida senha correta.
- [x] Login rejeita senha incorreta.
- [x] Usuario comum sem membership ativo nao recebe tokens finais.

## Verification

```bash
pytest
```

## Risks & Rollback

- **Risks**: divergencia entre estados de usuario e memberships.
- **Rollback**: desabilitar endpoints de auth ou reverter a migration/implementacao de Stage 02 em ambiente nao produtivo.

## Execution Log

- `[2026-05-07 12:30]`: Registro, login e hashing implementados.
