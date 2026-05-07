# Task: TASK-065 - I18n Locale Runtime Implementation

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-065 |
| **Group** | CORE |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_05_base_multitenant_workflows.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-08 |
| **Updated At** | 2026-05-08 |

## Context

TASK-063 definiu o contrato de i18n. Esta task implementa a infraestrutura minima para locales globais, preferencias por tenant/usuario e mensagens traduziveis usadas pelo frontend e comunicacoes transacionais.

## Objectives

- [ ] Criar migration com `system_settings.default_locale`, `system_settings.supported_locales`, `tenants.default_locale`, `users.default_locale` e tabela `i18n_messages`.
- [ ] Criar resolver de locale com ordem usuario -> tenant -> system default -> `pt-BR`.
- [ ] Criar endpoints superadmin para listar/upsert traducoes e configurar locales globais.
- [ ] Criar endpoint publico seguro para bootstrap de locales do frontend.
- [ ] Integrar templates de e-mail a variantes por locale.
- [ ] Registrar audit global para mudancas superadmin e audit/version tenant-scoped quando houver preferencia tenant.

## Non-Goals

- Traduzir todos os textos existentes.
- Criar UI de gerenciamento.
- Alterar formato base dos envelopes `ApiResponse` e `ApiErrorResponse`.

## Stage Boundaries

A task implementa apenas a fundacao de i18n definida no Stage 05. Nao cria sistema de CMS ou motor externo de traducao.

## Dependencies

- TASK-063
- TASK-062

## Inputs & Contracts

- **Inputs**: `system_settings`, `tenants`, `users`, templates de e-mail e mensagens de frontend.
- **Outputs**: endpoints versionados, mensagens traduziveis e resolucao deterministica de locale.
- **Schemas**: `I18nMessageRequest`, `I18nMessageResponse`, `LocaleSettingsRequest`, `LocaleBootstrapResponse`.

## Constraints & Rules

1. Locale deve validar BCP 47 simplificado.
2. Mensagens publicas nao podem conter segredos.
3. Superadmin gerencia mensagens globais; tenant settings so podem afetar o tenant selecionado.
4. Toda rota criada deve ter OpenAPI e Bruno.
5. Mudancas devem preservar isolamento tenant e auditoria.

## Implementation Checklist

- [ ] Criar migration.
- [ ] Criar repository de i18n.
- [ ] Criar schemas Pydantic.
- [ ] Criar endpoints superadmin.
- [ ] Criar endpoint publico de bootstrap.
- [ ] Integrar email templates por locale.
- [ ] Criar Bruno requests.
- [ ] Criar testes.

## Acceptance Criteria

- [ ] Locale e mensagens podem ser configurados por superadmin.
- [ ] Frontend consegue buscar bootstrap publico de locales.
- [ ] Resolver escolhe locale correto com fallback deterministico.
- [ ] Templates de e-mail conseguem selecionar variante por locale.
- [ ] OpenAPI, Bruno e testes cobrem contratos.

## Verification

```bash
cd backend
.\.venv\Scripts\python -m pytest tests/test_i18n.py -q
cd ..
backend\.venv\Scripts\python scripts\validate_openapi.py
python scripts\validate_tasks.py
```

## Risks & Rollback

- **Risks**: aumento de complexidade em mensagens transacionais e frontend bootstrap.
- **Rollback**: manter `pt-BR` como locale unico e ignorar mensagens inativas.

## Execution Log

- `[2026-05-08 00:00]`: Task criada a partir do contrato fechado em TASK-063.
