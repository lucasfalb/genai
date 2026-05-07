# Task: TASK-063 - I18n Platform Messages e Locale Settings

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-063 |
| **Group** | CORE |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_05_base_multitenant_workflows.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

A plataforma ja possui templates de e-mail gerenciaveis e `system_settings` para configuracoes globais. O proximo passo e preparar internacionalizacao para mensagens de sistema, templates transacionais, preferencias de locale e exibicao consistente no frontend.

I18n deve nascer como infraestrutura de produto, nao como textos soltos em codigo. O superadmin precisa controlar idiomas habilitados e fallback global; tenants podem futuramente ter preferencia de locale, sem quebrar isolamento multitenant.

## Objectives

- [ ] Definir modelo de locales suportados, locale padrao e fallback global.
- [ ] Definir contrato para traducoes de mensagens da API, templates de e-mail e labels publicos.
- [ ] Permitir configuracao global de idiomas em `system_settings`.
- [ ] Planejar preferencia de locale por tenant e por usuario.
- [ ] Definir estrategia de fallback quando traducao nao existir.
- [ ] Definir testes para resolucao de locale, fallback e templates traduzidos.

## Non-Goals

- Implementar UI completa de traducao.
- Traduzir todo o produto nesta task.
- Alterar contratos de auth, RBAC ou convites fora do necessario para resolver locale.

## Stage Boundaries

Esta task planeja a base de i18n para workflows multitenant e comunicacoes. A implementacao deve ser feita em task posterior, com migration propria e endpoints documentados.

## Dependencies

- TASK-062

## Inputs & Contracts

- **Inputs**: `system_settings`, templates de e-mail, mensagens de erro/sucesso da API, preferencias futuras de tenant/usuario.
- **Outputs**: contrato documentado para locales, fallback, storage de traducoes e exposicao segura ao frontend.
- **Schemas propostos**:
  - `system_settings.default_locale`
  - `system_settings.supported_locales`
  - `tenants.default_locale`
  - tabela futura para traducoes versionaveis, se necessario.

## Constraints & Rules

1. Locale deve usar formato BCP 47 simplificado, por exemplo `pt-BR`, `en-US` e `es-ES`.
2. Fallback global deve ser deterministico.
3. Templates transacionais devem permitir variantes por locale sem duplicar logica de envio.
4. Mensagens publicas expostas ao frontend nao podem incluir segredos ou dados tenant-scoped indevidos.
5. Alteracoes feitas por superadmin em mensagens/traducoes devem registrar audit global; alteracoes tenant-scoped devem registrar audit/version do tenant quando existirem.
6. Bruno e OpenAPI devem ser atualizados quando endpoints de i18n forem criados.

## Implementation Checklist

- [ ] Documentar arquitetura de i18n e fallback.
- [ ] Definir migration para locales globais e preferencia tenant/user.
- [ ] Definir se traducoes ficam em tabela dedicada ou em JSONB versionado.
- [ ] Definir endpoints superadmin para gerir locales/traducoes.
- [ ] Definir endpoint publico seguro para bootstrap de locale do frontend.
- [ ] Definir integracao com templates de e-mail.
- [ ] Criar testes de resolucao de locale e fallback.

## Acceptance Criteria

- [ ] Arquitetura de i18n cobre API, e-mail templates e bootstrap do frontend.
- [ ] Contrato diferencia configuracao global, preferencia tenant e preferencia usuario.
- [ ] Fallback de locale e comportamento sem traducao estao definidos.
- [ ] Regras de audit/version para superadmin e tenant-scoped estao definidas.
- [ ] Proxima task de implementacao pode ser criada sem ambiguidade.

## Verification

```bash
python scripts\validate_tasks.py
```

## Risks & Rollback

- **Risks**: modelar i18n de forma rigida demais pode gerar migrations frequentes; modelar solto demais pode dificultar validacao e fallback.
- **Rollback**: manter textos atuais como fallback unico ate a infraestrutura de i18n estar validada.

## Execution Log

- `[2026-05-07 22:10]`: Task futura criada para planejar i18n de mensagens, templates e preferencias de locale.
