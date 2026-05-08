# Task: TASK-026 - Account Activation Flow

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-026 |
| **Group** | AUTH |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_05_base_multitenant_workflows.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-08 |

## Context

O registro cria usuario `pending`, mas nao existe fluxo para confirmar email e ativar a conta usando o template `account_activation`.

## Objectives

- [x] Emitir token de ativacao no registro ou por request dedicado.
- [x] Criar endpoint para solicitar/reemitir ativacao.
- [x] Criar endpoint para confirmar ativacao.
- [x] Atualizar status do usuario para `active` quando token valido for consumido.
- [x] Renderizar placeholders `{{ variable }}` do template `account_activation` antes do envio.

## Non-Goals

- Criar UI de ativacao.
- Implementar provider real de email.

## Stage Boundaries

Esta task fecha lifecycle de conta dentro do dominio de auth base.

## Dependencies

- TASK-025

## Inputs & Contracts

- **Inputs**: email ou token de ativacao.
- **Outputs**: usuario ativo ou resposta neutra para evitar enumeracao.
- **Schemas**: Pydantic requests/responses de activation.

## Constraints & Rules

1. Request de ativacao deve ser idempotente e nao revelar se email existe.
2. Confirmacao deve consumir token uma unica vez.
3. Usuarios inativos nao devem receber access token final.
4. Bruno deve conter requests dos endpoints criados.

## Implementation Checklist

- [x] Criar schemas `ActivationRequest` e `ActivationConfirmRequest`.
- [x] Criar endpoints `/auth/activation/request` e `/auth/activation/confirm`.
- [x] Integrar token repository e email outbox.
- [x] Adicionar testes de sucesso, token invalido, expirado e reutilizado.
- [x] Atualizar `genai-endpoints/Auth`.

## Acceptance Criteria

- [x] Usuario pending consegue ativar conta com token valido.
- [x] Token invalido, expirado ou ja consumido e rejeitado.
- [x] Resposta de request nao permite enumeracao de emails.
- [x] OpenAPI e Bruno ficam atualizados.
- [x] Email de ativacao nao exibe placeholders crus como `{ platform_name }`, `{ user_name }` ou `{ expires_in }`.

## Verification

```bash
cd backend
pytest tests/test_stage_05_account_activation.py
cd ..
backend\.venv\Scripts\python scripts\validate_openapi.py
```

## Risks & Rollback

- **Risks**: ativacao permissiva pode liberar usuarios sem confirmacao.
- **Rollback**: manter usuarios pending e bloquear login ate corrigir fluxo.

## Execution Log

- `[2026-05-07 15:40]`: Task criada para cobrir lacuna de verificacao de email do Stage 02.
- `[2026-05-07 16:35]`: Endpoints de request/confirm implementados; registro enfileira ativacao e login/refresh bloqueiam usuarios inativos.
- `[2026-05-07 16:35]`: Bruno atualizado com `Request Activation` e `Confirm Activation`; testes e OpenAPI passaram.
- `[2026-05-08 20:00]`: Renderizador de email corrigido para processar placeholders `{{ variable }}` dos templates gerenciaveis, mantendo compatibilidade com `{ variable }` em templates ja salvos. Testes de auth tokens e ativacao executados com sucesso.
