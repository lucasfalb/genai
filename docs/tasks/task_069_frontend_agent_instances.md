# Task: TASK-069 - Agent Instances Management UI

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-069 |
| **Group** | FRONTEND |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_09_frontend.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-08 |
| **Updated At** | 2026-05-08 |

## Context

Instancias de agente sao o nucleo operacional do produto. Esta task implementa a listagem, criacao, detalhe/edicao, arquivamento e configuracao de prompt das instancias do tenant ativo.

## Objectives

- [x] Criar `frontend/src/lib/api/instances.ts` com funcoes tipadas para os endpoints de instancias.
- [x] Implementar rota `/instances` com listagem tenant-scoped.
- [x] Implementar rota `/instances/new` com formulario de criacao.
- [x] Implementar rota `/instances/{id}` com tabs: Config, Prompt Config e Skills/Tools.
- [x] Ajustar listagem, criacao e detalhe de Agent para layout operacional inspirado no Copilot Studio.
- [x] Carregar modelos, templates e painel de teste de `system_settings.public_settings.agent_ui`.
- [x] Implementar editor de instruction blocks com adicionar, editar, deletar e reordenar.
- [x] Implementar editor de guardrails com toggle, edicao de regra e remocao.

## Non-Goals

- Nao implementar a aba Skills/Tools; ela fica como stub para TASK-070.
- Nao implementar chat; isso pertence a TASK-074.
- Nao implementar upload ou gestao de documentos RAG; isso pertence a TASK-073.

## Stage Boundaries

Apenas gestao de instancias e prompt config. Ativacao de skills/tools e demais recursos continuam em tasks posteriores.

## Dependencies

- TASK-068 - Tenant ativo e headers tenant-scoped funcionando.

## Inputs & Contracts

**Arquivo `frontend/src/lib/api/instances.ts`:**

```typescript
export const instancesApi = {
  list,
  create,
  get,
  update,
  delete,
  getPromptConfig,
  savePromptConfig,
};
```

**Rotas e arquivos implementados:**

- `frontend/src/routes/(app)/instances/+page.server.ts`
- `frontend/src/routes/(app)/instances/+page.svelte`
- `frontend/src/routes/(app)/instances/new/+page.svelte`
- `frontend/src/routes/(app)/instances/[id]/+page.server.ts`
- `frontend/src/routes/(app)/instances/[id]/+page.svelte`
- `frontend/src/lib/server/api.ts`

## Constraints & Rules

1. Chamadas de instancia exigem `X-Tenant-ID`; o client injeta no browser e `tenantBackendRequest()` injeta no SSR.
2. Listagem e detalhe carregam via SSR para renderizar com dados do tenant ativo.
3. Delete exige confirmacao antes de arquivar a instancia.
4. Temperature e validada no frontend entre `0` e `2`.
5. Prompt config normaliza priorities dos instruction blocks como `1..N` antes de salvar.
6. Guardrails sem categoria ou regra nao sao enviados ao backend.
7. Aba Skills/Tools fica visivel apenas como placeholder para TASK-070.
8. Defaults de UI de agentes devem vir de `public_settings.agent_ui`; fallback local so existe para resiliencia quando o backend nao retornar a key.

## Implementation Checklist

- [x] Criar `frontend/src/lib/api/instances.ts` com todos os 7 metodos.
- [x] Criar helper SSR `frontend/src/lib/server/api.ts` para chamadas tenant-scoped.
- [x] Criar `frontend/src/routes/(app)/instances/+page.server.ts`:
  - [x] Carregar lista via backend com Bearer token e `X-Tenant-ID`.
- [x] Criar `frontend/src/routes/(app)/instances/+page.svelte`:
  - [x] Exibir lista operacional de agents.
  - [x] Exibir status badge.
  - [x] Link para nova instancia.
  - [x] Link para detalhe.
- [x] Criar `frontend/src/routes/(app)/instances/new/+page.svelte`:
  - [x] Form com campos de `AgentInstanceCreateRequest`.
  - [x] Templates carregados de `system_settings.public_settings.agent_ui`.
  - [x] Modelos carregados de `system_settings.public_settings.agent_ui`.
  - [x] Submit cria instancia e redireciona para detalhe.
  - [x] Erros aparecem em alert inline.
- [x] Criar `frontend/src/routes/(app)/instances/[id]/+page.server.ts`:
  - [x] Carregar instancia.
  - [x] Carregar prompt config.
- [x] Criar `frontend/src/routes/(app)/instances/[id]/+page.svelte`:
  - [x] Aba Config com edicao e delete.
  - [x] Aba Prompt Config com instruction blocks e guardrails inline.
  - [x] Aba Skills/Tools como stub para TASK-070.
  - [x] Alert de sucesso/erro apos operacoes.
  - [x] Secao Knowledge aponta para collections do tenant.
  - [x] Header, tabs e painel lateral de teste seguem o padrao visual Copilot Studio.

## Acceptance Criteria

- [x] Listagem de instancias exibe instancias do tenant ativo.
- [x] Criacao de instancia redireciona para a pagina de detalhe.
- [x] Edicao de instancia persiste no backend e exibe confirmacao.
- [x] Delecao exige confirmacao e redireciona para `/instances`.
- [x] Instruction blocks podem ser adicionados, editados, deletados e reordenados.
- [x] Guardrails podem ser ativados/desativados, editados e removidos.
- [x] Salvar prompt config persiste no backend com priorities normalizadas.
- [x] Campos invalidos sao bloqueados antes do submit.
- [x] Detalhe do Agent expoe Knowledge internamente, sem item Knowledge no aside.
- [x] Criacao de Agent usa templates e modelos configuraveis pelo superadmin em `public_settings.agent_ui`.
- [x] Detalhe do Agent exibe area de edicao principal e painel lateral de teste quando `test_panel_enabled=true`.

## Verification

```bash
cd frontend
npm run check
npm run test:unit
```

## Risks & Rollback

- **Risco**: dados carregados por SSR ficarem obsoletos apos mutacao client-side. Mitigacao: mutacoes atualizam estado local e proximos reloads buscam dados frescos.
- **Risco**: prompt config com campos vazios. Mitigacao: normalizacao filtra blocos/guardrails invalidos antes do submit.
- **Rollback**: reverter rotas de instances e helper SSR.

## Execution Log

- `[2026-05-08 00:00]`: Task criada.
- `[2026-05-08 13:06]`: Listagem e detalhe migrados para SSR tenant-scoped, editor de prompt config completado inline, validacoes adicionadas e TASK-069 concluida apos `npm run check` e `npm run test:unit`.
- `[2026-05-08 20:35]`: Terminologia ajustada de Instances para Agents no app, detalhe recebeu secao Knowledge com link para `/collections`, e `/app/{tenant}`/dashboard passaram a direcionar para Agents.
- `[2026-05-08 21:40]`: Interface de Agents revisada para lista operacional, fluxo de criacao com templates configuraveis e detalhe no padrao Copilot Studio com painel lateral de teste.
