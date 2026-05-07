# Task: TASK-025 - Auth Token Tables e Email Event Outbox

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-025 |
| **Group** | AUTH |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_05_base_multitenant_workflows.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Fluxos de ativacao, convite e reset exigem tokens transacionais single-use e registro de comunicacoes. Templates de email ja existem, mas falta persistencia operacional para emissao, reenvio, expiracao e auditoria.

## Objectives

- [x] Criar tabela para tokens transacionais de auth com hash, tipo, expiracao e consumo.
- [x] Criar outbox de email transacional baseada em `email_templates`.
- [x] Criar repositorios para criar, consumir e invalidar tokens.
- [x] Garantir que tokens em claro nunca sejam persistidos ou logados.

## Non-Goals

- Enviar email real via provider externo.
- Implementar frontend de ativacao ou reset.

## Stage Boundaries

Esta task prepara persistencia e contratos internos para workflows de auth, sem expor endpoints finais.

## Dependencies

- TASK-011

## Inputs & Contracts

- **Inputs**: user id, tenant id opcional, template slug, finalidade do token.
- **Outputs**: token em claro retornado apenas ao chamador interno, hash persistido, email event pendente.
- **Schemas**: migrations, repositorios de token transacional e email outbox.

## Constraints & Rules

1. Tokens devem ser hashados com algoritmo resistente a lookup direto.
2. Tokens devem ser single-use e expirar.
3. Email outbox deve referenciar template gerenciavel.
4. Payloads nao podem conter senha, token hash ou segredo.

## Implementation Checklist

- [x] Criar migration de `auth_action_tokens`.
- [x] Criar migration de `email_events` ou outbox equivalente.
- [x] Criar repositorio de tokens.
- [x] Criar repositorio de email outbox.
- [x] Criar testes de expiracao, consumo unico e redaction.

## Acceptance Criteria

- [x] Token em claro nunca e salvo no banco.
- [x] Token consumido nao pode ser reutilizado.
- [x] Token expirado e rejeitado.
- [x] Email outbox referencia template existente.

## Verification

```bash
cd backend
pytest tests/test_stage_05_auth_tokens.py
```

## Risks & Rollback

- **Risks**: token reutilizavel ou logado pode comprometer contas.
- **Rollback**: desabilitar endpoints dependentes e remover tokens pendentes.

## Execution Log

- `[2026-05-07 15:40]`: Task criada apos revisao de lacunas de auth lifecycle.
- `[2026-05-07 16:00]`: Migration `20260507_0006` criada com `auth_action_tokens` e `email_events`.
- `[2026-05-07 16:00]`: Repositorios `AuthActionTokenRepository` e `EmailEventRepository` implementados em `database/repositories/auth_tokens.py`.
- `[2026-05-07 16:00]`: Helper `create_action_token()` adicionado em `app/security.py`.
- `[2026-05-07 16:00]`: Config `action_token_expire_minutes` adicionada em `app/config.py`.
- `[2026-05-07 16:00]`: Testes `test_stage_05_auth_tokens.py` com 9 cenarios (criacao, consumo unico, expiracao, hash-only, invalidate-all, email events lifecycle, payload sem segredos).
- `[2026-05-07 16:00]`: Todos os 9 testes passando.
- `[2026-05-07 16:35]`: Revisao de implementacao encontrou lacunas e adicionou hardening: `tenant_id` opcional, constraints de tipo/status, consumo filtravel por tipo e rejeicao de payload sensivel no repositorio de email events.
