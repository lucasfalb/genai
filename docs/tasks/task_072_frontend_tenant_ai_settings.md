# Task: TASK-072 — Tenant AI Settings UI

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-072 |
| **Group** | FRONTEND |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_09_frontend.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | MEDIUM |
| **Owner** | Unassigned |
| **Created At** | 2026-05-08 |
| **Updated At** | 2026-05-08 |

## Context

Tenants podem configurar seu proprio provedor de IA (OpenAI, Azure, etc.) em vez de usar o provedor da plataforma. Esta task implementa o formulario de configuracao de AI por tenant, conectado aos 3 endpoints do grupo `tenant-ai-settings` (`GET /tenant/settings/ai`, `PUT /tenant/settings/ai`, `DELETE /tenant/settings/ai`).

## Objectives

- [x] Criar `frontend/src/lib/api/aiSettings.ts` com funcoes tipadas para os 3 endpoints de AI settings.
- [x] Implementar pagina `/settings/ai` com formulario de configuracao: provider, api_key, default_model, enabled toggle.
- [x] Exibir indicador visual `has_api_key` (chave ja configurada sem expor o valor).
- [x] Implementar DELETE para remover a configuracao de AI do tenant.

## Non-Goals

- Nao implementar configuracoes de AI para superadmin (TASK-075).
- Nao validar se a api_key e valida junto ao provedor — o backend faz isso.
- Nao implementar rotacao automatica de chaves.

## Stage Boundaries

Apenas configuracao de AI tenant-scoped. Sem alteracoes no backend.

## Dependencies

- TASK-068 — contexto de tenant ativo, guard de autenticacao.

## Inputs & Contracts

**Arquivo `frontend/src/lib/api/aiSettings.ts`:**
```typescript
import { api } from '$lib/api/client';
import type { TenantAIConfigResponse, TenantAIConfigRequest } from '$lib/api/types';

export const aiSettingsApi = {
  get:    () => api.get<TenantAIConfigResponse>('/tenant/settings/ai'),
  save:   (body: TenantAIConfigRequest) => api.put<TenantAIConfigResponse>('/tenant/settings/ai', body),
  delete: () => api.del<void>('/tenant/settings/ai'),
};
```

**Pagina `(app)/app/[tenant]/settings/ai/+page.svelte`:**
- GET carregado via `+page.server.ts` (SSR) com `tenantBackendRequest`. 404 tratado como `null`.
- Se `has_api_key === true`: exibir badge verde "Key configured".
- Se `has_api_key === false`: exibir badge cinza "No key".
- Formulario:
  - `provider`: select com opcoes (openai, azure, anthropic, cohere, mistral, groq).
  - `api_key`: input `type="password"` — sempre vazio ao renderizar (nunca retornado pelo backend). Campo **sempre obrigatorio** — backend rejeita strings vazias (`min_length=1`).
  - `default_model`: input text (ex: gpt-4o-mini).
  - `enabled`: toggle switch boolean.
- Botao "Save Configuration" → PUT `/tenant/settings/ai` → atualiza estado local.
- Botao "Remove Configuration" (visivel apenas se `config.provider != null`) → confirm() → DELETE → reset estado local.

**Campos de `TenantAIConfigResponse` (tipos corrigidos apos verificacao do backend):**
- `tenant_id`: string
- `provider`: string | null — null quando sem configuracao
- `default_model`: string | null
- `enabled`: boolean
- `has_api_key`: boolean — indica se ha chave salva (NAO retorna o valor da chave)
- `configured_by`: string | null — UUID do usuario que configurou

**Campos de `TenantAIConfigRequest`:**
- `provider`: string — obrigatorio, pattern `^[a-z0-9_-]+$`, max 80 chars
- `api_key`: string — obrigatorio, `min_length=1`, `max_length=512`
- `default_model`: string | null — opcional
- `enabled`: boolean

## Constraints & Rules

1. Campo `api_key` NUNCA e exibido em texto claro — `type="password"` obrigatorio.
2. Backend tem `api_key: str = Field(min_length=1)` — string vazia causa 422. O campo e **sempre obrigatorio** ao salvar; validacao client-side bloqueia submit com campo vazio e exibe toast de erro.
3. Para alterar apenas `enabled` ou `default_model`, o usuario deve re-inserir a api_key. A chave nao e recuperavel por design de seguranca.
4. Badge de "Key configured" deve ser verde; "No key" deve ser cinza.
5. `configured_by` exibido como texto auxiliar no status card.
6. GET retorna 200 com `provider: null` quando sem configuracao (nao 404). 404 e tratado como null no loader para robustez.
7. Remocao da config implica que o tenant voltara a usar a config da plataforma — comunicar isso claramente no confirm().
8. Backend usa `Permission.MANAGE_AGENT_INSTANCES` para proteger os 3 endpoints — role `tenant_admin` ou superior.

## Implementation Checklist

- [x] Criar `frontend/src/lib/api/aiSettings.ts` com metodos `get`, `save`, `delete`.
- [x] Criar `frontend/src/routes/(app)/app/[tenant]/settings/ai/+page.server.ts`:
  - [x] Carregar config via `tenantBackendRequest` — tratar 404 como null.
- [x] Criar `frontend/src/routes/(app)/app/[tenant]/settings/ai/+page.svelte`:
  - [x] Mostrar estado atual: badge "Key configured" (verde) ou "No key" (cinza), `configured_by`, status de habilitacao.
  - [x] Form: select de provider (openai | azure | anthropic | cohere | mistral | groq), input api_key (password, obrigatorio), input default_model, toggle enabled (Switch shadcn).
  - [x] Validacao client-side: campo api_key vazio → toast de erro, nao submete.
  - [x] Botao "Save Configuration" → `aiSettingsApi.save()` → toast sucesso/erro → atualiza estado local (`config = updated`, limpa apiKey).
  - [x] Botao "Remove Configuration" (condicional: apenas se `config.provider != null`):
    - [x] `confirm()` com aviso sobre fallback para plataforma.
    - [x] `aiSettingsApi.delete()` → toast → reset estado local para defaults.
  - [x] Exibir `configured_by` no status card.
- [x] Atualizar `frontend/src/lib/api/types.ts` — tipos nullable em `TenantAIConfigResponse` e `TenantAIConfigRequest`.
- [x] Adicionar link "AI Settings" para `/settings/ai` no menu System do layout `(app)/+layout.svelte`.

## Acceptance Criteria

- [x] Pagina carrega a config existente sem expor o valor da api_key.
- [x] Badge "Key configured" (verde) exibido quando `has_api_key === true`; badge "No key" (cinza) caso contrario.
- [x] Campo api_key sempre obrigatorio — submit bloqueado com campo vazio, toast de erro exibido.
- [x] Salvar com api_key preenchida atualiza a configuracao no backend.
- [x] Toggle `enabled` e demais campos salvos juntos no PUT.
- [x] Remocao exige confirmacao com mensagem sobre fallback para provedor da plataforma.
- [x] Pagina sem config existente (`provider === null`) exibe formulario vazio com defaults razoaveis (`provider: openai`, `enabled: true`).

## Verification

```bash
cd frontend
npm run check
# 0 errors esperados
# Teste manual: configurar AI provider, verificar has_api_key badge, remover config
```

Resultado da verificacao: `0 ERRORS 59 WARNINGS` (warnings sao pre-existentes no projeto).

## Risks & Rollback

- **Risco resolvido**: Contrato do backend verificado — `api_key` tem `min_length=1` e o `UPDATE` SQL nao usa `COALESCE` (sempre sobrescreve). Enviar `""` causaria 422. Solucao: validacao client-side obriga preenchimento.
- **Risco**: Provider invalido pode causar erro 422. Mitigacao: lista hardcoded de providers suportados no select (openai, azure, anthropic, cohere, mistral, groq).
- **Rollback**: Remover `frontend/src/lib/api/aiSettings.ts`, `frontend/src/routes/(app)/app/[tenant]/settings/ai/`, reverter alteracoes em `types.ts` e `+layout.svelte` — sem alteracoes no backend.

## Execution Log

- `[2026-05-08 00:00]`: Task criada.
- `[2026-05-08 12:00]`: Implementacao concluida. Arquivos criados: `frontend/src/lib/api/aiSettings.ts`, `+page.server.ts`, `+page.svelte`. Nav link adicionado ao layout. Tipos `TenantAIConfigResponse` corrigidos para nullable (`provider | null`, `default_model | null`, `configured_by | null`); `TenantAIConfigRequest.default_model` tambem `string | null`. Contrato do backend verificado: `api_key` tem `min_length=1` — frontend valida antes de submeter e exige re-entrada da chave para salvar. `npm run check`: 0 erros.
