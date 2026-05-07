# Task: TASK-063 - I18n Platform Messages e Locale Settings

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-063 |
| **Group** | CORE |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_05_base_multitenant_workflows.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Codex |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-08 |

## Context

A plataforma ja possui templates de e-mail gerenciaveis e `system_settings` para configuracoes globais. I18n deve nascer como infraestrutura de produto, nao como textos soltos em codigo. O superadmin controla idiomas habilitados e fallback global; tenants e usuarios poderao ter preferencias sem quebrar isolamento multitenant.

## Objectives

- [x] Definir modelo de locales suportados, locale padrao e fallback global.
- [x] Definir contrato para traducoes de mensagens da API, templates de e-mail e labels publicos.
- [x] Permitir configuracao global de idiomas em `system_settings`.
- [x] Planejar preferencia de locale por tenant e por usuario.
- [x] Definir estrategia de fallback quando traducao nao existir.
- [x] Definir testes para resolucao de locale, fallback e templates traduzidos.

## Non-Goals

- [x] Implementar UI completa de traducao.
- [x] Traduzir todo o produto nesta task.
- [x] Alterar contratos de auth, RBAC ou convites fora do necessario para resolver locale.

## Stage Boundaries

Esta task fecha o desenho de i18n para workflows multitenant e comunicacoes. A implementacao fica em task posterior com migration propria, endpoints documentados, Bruno e testes.

## Dependencies

- TASK-062

## Inputs & Contracts

- **Inputs**: `system_settings`, templates de e-mail, mensagens de erro/sucesso da API, preferencias futuras de tenant/usuario.
- **Outputs**: contrato documentado para locales, fallback, storage de traducoes e exposicao segura ao frontend.
- **Schemas definidos para implementacao futura**:
  - `system_settings.default_locale TEXT NOT NULL DEFAULT 'pt-BR'`
  - `system_settings.supported_locales JSONB NOT NULL DEFAULT '["pt-BR"]'`
  - `tenants.default_locale TEXT NULL`
  - `users.default_locale TEXT NULL`
  - `i18n_messages(id, namespace, message_key, locale, value, metadata, is_active, updated_by, created_at, updated_at)`

## Constraints & Rules

1. Locale deve usar formato BCP 47 simplificado, por exemplo `pt-BR`, `en-US` e `es-ES`.
2. Fallback global deve ser deterministico: usuario -> tenant -> system default -> `pt-BR`.
3. Templates transacionais devem permitir variantes por locale sem duplicar logica de envio.
4. Mensagens publicas expostas ao frontend nao podem incluir segredos ou dados tenant-scoped indevidos.
5. Alteracoes feitas por superadmin em mensagens/traducoes devem registrar audit global; alteracoes tenant-scoped devem registrar audit/version do tenant quando existirem.
6. Bruno e OpenAPI devem ser atualizados quando endpoints de i18n forem criados.

## Implementation Checklist

- [x] Documentar arquitetura de i18n e fallback.
- [x] Definir migration para locales globais e preferencia tenant/user.
- [x] Definir traducoes em tabela dedicada versionavel, nao em JSONB solto.
- [x] Definir endpoints superadmin para gerir locales/traducoes.
- [x] Definir endpoint publico seguro para bootstrap de locale do frontend.
- [x] Definir integracao com templates de e-mail.
- [x] Criar escopo de testes de resolucao de locale e fallback.

## Acceptance Criteria

- [x] Arquitetura de i18n cobre API, e-mail templates e bootstrap do frontend.
- [x] Contrato diferencia configuracao global, preferencia tenant e preferencia usuario.
- [x] Fallback de locale e comportamento sem traducao estao definidos.
- [x] Regras de audit/version para superadmin e tenant-scoped estao definidas.
- [x] Proxima task de implementacao pode ser criada sem ambiguidade.

## Verification

```bash
python scripts\validate_tasks.py
```

## Risks & Rollback

- **Risks**: modelar i18n de forma rigida demais pode gerar migrations frequentes; modelar solto demais pode dificultar validacao e fallback.
- **Rollback**: manter textos atuais como fallback unico ate a infraestrutura de i18n estar validada.

## Execution Log

- `[2026-05-07 22:10]`: Task futura criada para planejar i18n de mensagens, templates e preferencias de locale.
- `[2026-05-08 00:00]`: Contrato de i18n fechado com fallback deterministico, tabela dedicada de mensagens e escopo de implementacao futura.
