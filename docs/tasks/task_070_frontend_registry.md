# Task: TASK-070 — Registry Management UI

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-070 |
| **Group** | FRONTEND |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_09_frontend.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-08 |
| **Updated At** | 2026-05-08 |

## Context

Skills e tools sao as capacidades extensiveis de cada instancia de agente. Esta task implementa a aba Skills/Tools dentro da pagina de detalhe da instancia (criada como stub em TASK-069), e a pagina de gestao de credenciais por skill_slug. Cobre os 5 endpoints do grupo `tenant-registry`.

## Objectives

- [x] Criar `frontend/src/lib/api/registry.ts` com funcoes tipadas para os 5 endpoints de registry.
- [x] Preencher a aba Skills/Tools na pagina `/instances/{id}` com dados reais do endpoint de metadata.
- [x] Implementar toggle de ativacao de skill/tool com chamada PUT ao backend.
- [x] Implementar edicao de `config` (JSON) por skill/tool ativado.
- [x] Implementar pagina `/settings/credentials` — listagem e edicao de credenciais por skill_slug.

## Non-Goals

- Nao implementar criacao ou definicao de novas skills/tools (isso e superadmin — TASK-075).
- Nao implementar validacao do JSON de config contra o schema da skill/tool.
- Nao implementar Vault de segredos — `secret_ref` e um campo texto simples.

## Stage Boundaries

Apenas consumo dos 5 endpoints de registry. Sem novos endpoints no backend.

## Dependencies

- TASK-069 — pagina `/instances/{id}` existe com aba Skills/Tools como stub.

## Inputs & Contracts

**Arquivo `frontend/src/lib/api/registry.ts`:**
```typescript
import { api } from '$lib/api/client';
import type {
  ToolMetadataResponse, ActivationRequest,
  CredentialResponse, CredentialRequest
} from '$lib/api/types';

export const registryApi = {
  getCredentials:   () => api.get<CredentialResponse[]>('/registry/credentials'),
  saveCredential:   (skillSlug: string, body: CredentialRequest) =>
    api.put<CredentialResponse>(`/registry/credentials/${skillSlug}`, body),
  getMetadata:      (instanceId: string) =>
    api.get<ToolMetadataResponse>(`/registry/instances/${instanceId}/metadata`),
  activateSkill:    (instanceId: string, skillSlug: string, body: ActivationRequest) =>
    api.put<SkillActivationResponse>(`/registry/instances/${instanceId}/skills/${skillSlug}`, body),
  activateToolItem: (instanceId: string, toolSlug: string, body: ActivationRequest) =>
    api.put<ToolActivationResponse>(`/registry/instances/${instanceId}/tools/${toolSlug}`, body),
};
```

**Estrutura da aba Skills/Tools em `/instances/{id}/+page.svelte`:**
```
Skills/Tools Tab
├── Secao: Skills
│   └── [lista de skills do metadata]
│       ├── nome da skill, descricao (se disponivel)
│       ├── toggle is_enabled (on/off) → PUT /skills/{slug}
│       └── se enabled: botao "Configurar" → painel de config JSON
└── Secao: Tools
    └── [lista de tools do metadata]
        ├── nome da tool, descricao
        ├── toggle is_enabled → PUT /tools/{slug}
        └── se enabled: botao "Configurar" → painel de config JSON
```

**Pagina `/settings/credentials/+page.svelte`:**
- Carregar lista via `registryApi.getCredentials()`.
- Para cada credential: exibir `skill_slug`, `secret_ref` (masked como `****{ultimos 4 chars}`), metadata.
- Botao "Editar" abre modal: form com `secret_ref` (input text) e `metadata` (textarea JSON).
- Submit: `registryApi.saveCredential(skillSlug, { secret_ref, metadata })`.

**Componente de config JSON:**
```
ConfigPanel (expansivel)
├── textarea: JSON livre (validado como JSON valido antes de submit)
├── Botao Salvar → PUT /skills/{slug} ou /tools/{slug} com { is_enabled, config }
└── Mensagem de erro se JSON invalido
```

## Constraints & Rules

1. O toggle de `is_enabled` deve chamar o PUT imediatamente (sem botao Salvar separado para o toggle).
2. O `config` JSON e enviado junto com `is_enabled` em cada PUT — carregar config atual antes de enviar.
3. Se o JSON de config for invalido, bloquear o submit e exibir mensagem de erro.
4. `secret_ref` nunca e exibido em texto claro — usar `type="password"` no input ou mascarar.
5. O metadata de credencial e exibido como JSON formatado (readonly) na lista; editavel somente no modal.
6. Erros 404 no GET de metadata (instancia sem configuracao) devem ser tratados graciosamente — exibir "Sem skills/tools configurados" em vez de crash.
7. Recarregar metadata apos cada PUT de ativacao para refletir estado atual.

## Implementation Checklist

- [x] Criar `frontend/src/lib/api/registry.ts` com todos os 5 metodos.
- [x] Atualizar `frontend/src/routes/(app)/instances/[id]/+page.server.ts`:
  - [x] Adicionar chamada SSR ao endpoint `/registry/instances/{id}/metadata`.
- [x] Preencher aba Skills/Tools em `frontend/src/routes/(app)/instances/[id]/+page.svelte`:
  - [x] Renderizar lista de skills do `ToolMetadataResponse.skills`.
  - [x] Toggle `is_enabled` por skill → `registryApi.activateSkill(instanceId, slug, { is_enabled, config })`.
  - [x] Expandir painel de config JSON para skill.
  - [x] Renderizar lista de tools de `ToolMetadataResponse.tools`.
  - [x] Toggle `is_enabled` por tool → `registryApi.activateToolItem(instanceId, slug, { is_enabled, config })`.
  - [x] Expandir painel de config JSON para tool.
  - [x] Feedback visual (busy state, toast de sucesso/erro) em cada toggle/save.
- [x] Criar componente `frontend/src/lib/components/JsonConfigPanel.svelte`:
  - [x] Props: `value: string` (JSON inicial), `onSave: (json: string) => Promise<void>`.
  - [x] Textarea com validacao JSON ao sair do campo.
  - [x] Botao Salvar desabilitado se JSON invalido.
  - [x] Exibir mensagem de erro de validacao inline.
- [x] Criar `frontend/src/routes/(app)/settings/credentials/+page.svelte`:
  - [x] Carregar lista via SSR em `+page.server.ts`.
  - [x] Tabela: skill_slug, secret_ref (mascarado), acoes.
  - [x] Painel de edicao: campos `secret_ref` e `metadata` (textarea JSON).
  - [x] Submit: `registryApi.saveCredential()` → fechar painel → atualizar lista local.

## Acceptance Criteria

- [x] Aba Skills/Tools exibe todas as skills e tools disponiveis para a instancia.
- [x] Toggle de skill ativa/desativa imediatamente com feedback visual.
- [x] Config JSON invalido e bloqueado com mensagem de erro antes do submit.
- [x] Credenciais sao listadas com `secret_ref` mascarado.
- [x] Edicao de credencial persiste no backend e atualiza a lista.
- [x] Erros de API sao exibidos como toasts ou alerts — sem crashes silenciosos.

## Verification

```bash
cd frontend
npm run check
npm run test:unit
cd ..
python scripts/validate_tasks.py
# Teste manual: ativar skill, configurar config JSON, editar credencial
```

## Risks & Rollback

- **Risco**: Config JSON com schema especifico pode ser invalido semanticamente mesmo sendo JSON valido. Mitigacao: validacao semantica e responsabilidade do backend; frontend valida apenas sintaxe.
- **Risco**: Race condition ao alternar toggles rapidamente. Mitigacao: desabilitar toggle durante o request em andamento.
- **Rollback**: Remover arquivos criados — sem alteracoes no backend.

## Execution Log

- `[2026-05-08 00:00]`: Task criada.
- `[2026-05-08 13:12]`: Implementado cliente registry, aba Skills/Tools com metadata SSR, toggles/config JSON e pagina de credenciais.
- `[2026-05-08 13:12]`: Verificado com `npm run check` e `npm run test:unit`.
