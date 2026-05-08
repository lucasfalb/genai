# Stage 09 — Frontend Integration

_Fonte canonica: [`../platform_technical_spec.md`](../platform_technical_spec.md). Este stage descreve a integracao do frontend SvelteKit com todos os endpoints da API REST do GenAI Platform._

## Objetivo

Implementar a camada de frontend completa em SvelteKit 5 (com Svelte runes), conectada a todos os 59 endpoints da API backend. Inclui: infraestrutura de cliente HTTP tipado, flows de autenticacao, gestao de tenants, instancias de agente, registry, members, convites, configuracoes AI, colecoes RAG, chat com SSE e painel superadmin.

## Stack Frontend

- **Framework**: SvelteKit 5 (file-based routing, SSR/CSR hibrido)
- **Estado**: Svelte 5 runes (`$state`, `$derived`, `$effect`) — sem Svelte stores legados
- **Estilizacao**: TailwindCSS + shadcn/svelte
- **HTTP**: fetch nativo com wrapper tipado (`frontend/src/lib/api/client.ts`)
- **Tipos**: TypeScript strict — interfaces em `frontend/src/lib/api/types.ts`
- **SSE**: `EventSource` / `fetch` + `ReadableStream` para chat streaming

## Estrutura de Diretorios

```
frontend/
├── src/
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts          # fetch wrapper tipado, auth injection, retry 401
│   │   │   ├── types.ts           # todos os tipos/interfaces de request e response
│   │   │   ├── auth.ts            # funcoes para os 11 endpoints de auth
│   │   │   ├── instances.ts       # funcoes para os 7 endpoints de instancias
│   │   │   ├── registry.ts        # funcoes para os 5 endpoints de registry
│   │   │   ├── members.ts         # funcoes para os 3 endpoints de members
│   │   │   ├── invitations.ts     # funcoes para os 4 endpoints de convites tenant
│   │   │   ├── aiSettings.ts      # funcoes para os 3 endpoints de AI settings
│   │   │   ├── collections.ts     # funcoes para os 5 endpoints de collections
│   │   │   ├── chat.ts            # SSE streaming para o endpoint de chat
│   │   │   └── superadmin.ts      # funcoes para os 14 endpoints superadmin
│   │   └── stores/
│   │       ├── auth.svelte.ts     # store de auth (user, tokens, memberships)
│   │       └── tenant.svelte.ts   # store de tenant ativo
│   └── routes/
│       ├── (public)/              # login, register, activation, password, invite
│       ├── (app)/app/[tenant]/    # dashboard, instances, settings, knowledge, chat por tenant
│       └── (admin)/admin/         # painel superadmin global
└── ...
```

## Tasks Deste Stage

| ID | Task | Prioridade |
| :--- | :--- | :--- |
| TASK-066 | API Client Infrastructure | CRITICAL |
| TASK-067 | Auth Flows API Wiring | CRITICAL |
| TASK-068 | Tenant Context & Invitation Flows | HIGH |
| TASK-069 | Agent Instances Management UI | HIGH |
| TASK-070 | Registry Management UI | HIGH |
| TASK-071 | Members & Invitations Team Management UI | MEDIUM |
| TASK-072 | Tenant AI Settings UI | MEDIUM |
| TASK-073 | Collections (RAG) Management UI | MEDIUM |
| TASK-074 | Agent Chat Interface (SSE) | HIGH |
| TASK-075 | Superadmin Panel UI | MEDIUM |
| TASK-076 | Frontend Route Topology | HIGH |

## Dependencias Entre Tasks

```text
TASK-066 (API Client)
   ↓
TASK-067 (Auth Flows)
   ↓
TASK-068 (Tenant Context) ──→ TASK-069 (Instances) ──→ TASK-070 (Registry)
   ↓                                ↓
TASK-071 (Members)           TASK-074 (Chat SSE)
TASK-072 (AI Settings)
TASK-073 (Collections)
TASK-067 ──→ TASK-075 (Superadmin)
```

## Convencoes Obrigatorias

1. **Nenhum endpoint novo no backend** — este stage apenas consome a API existente.
2. **Todas as chamadas API** passam pelo wrapper `client.ts` — nunca fetch direto nas rotas.
3. **X-Tenant-ID** e o **Bearer token** sao injetados automaticamente pelo `client.ts`.
4. **Token refresh automatico** em 401: tentar uma vez com novo access token antes de redirecionar ao login.
5. **Persistencia** de `access_token`, `refresh_token` e `activeTenantId` em `localStorage`.
6. **Svelte 5 runes**: usar `$state()` nos stores — nao `writable()` legado.
7. **Isolamento de tenant**: nenhuma pagina tenant-scoped renderiza fora de `/app/{tenantSlug}` ou sem `activeTenantId`.
8. **Superadmin guard**: rotas `/admin/*` so acessiveis se `authStore.user.is_superadmin === true`.

## Notas de Seguranca

- `api_key` nunca exibida em texto plano — mascarar campo no formulario (type=password).
- `has_api_key` do backend indica se ja ha chave configurada; exibir indicador visual.
- Tokens em `localStorage` — risco de XSS mitigado por Content-Security-Policy no servidor.
- Nunca logar tokens ou credenciais no console.
