# Task: TASK-067 - Auth Flows API Wiring

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-067 |
| **Group** | FRONTEND |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_09_frontend.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-08 |
| **Updated At** | 2026-05-08 |

## Context

Com o cliente HTTP e os stores criados na TASK-066, esta task conecta as telas de autenticacao aos endpoints reais do backend. Cobre login, registro, ativacao de conta, recuperacao e troca de senha, logout, hidratacao SSR de sessao e carregamento das configuracoes publicas da plataforma.

## Objectives

- [x] Criar `frontend/src/lib/api/auth.ts` com funcoes tipadas para os endpoints de auth.
- [x] Conectar pagina de login ao flow completo: `POST /auth/login` -> store -> redirect.
- [x] Conectar pagina de registro ao flow: `POST /auth/register` -> redirect.
- [x] Conectar paginas de ativacao de conta: request e confirm.
- [x] Conectar paginas de recuperacao: forgot-password, reset-password e change-password.
- [x] Implementar logout completo: `POST /auth/logout` -> clear stores -> redirect.
- [x] Hidratar sessao autenticada via SSR com `GET /auth/me` e `GET /auth/me/tenants`.
- [x] Carregar configuracoes publicas da plataforma com `GET /system-settings/public` no layout de auth.

## Non-Goals

- Nao implementar UI alem de conectar os forms aos endpoints existentes.
- Nao implementar CRUD de tenants, members ou convites administrativos; isso pertence a tasks seguintes.
- Nao substituir o contrato de API definido pela TASK-066.

## Stage Boundaries

Apenas wiring de endpoints de auth, public settings e guards SSR de autenticacao. Logica de tenant selection avancada e convites publicos continuam em TASK-068.

## Dependencies

- TASK-066 - `client.ts`, `types.ts`, `auth.svelte.ts` e `tenant.svelte.ts`.

## Inputs & Contracts

**Arquivo `frontend/src/lib/api/auth.ts`:**

```typescript
export const authApi = {
  login,
  register,
  logout,
  refresh,
  me,
  myTenants,
  activationRequest,
  activationConfirm,
  passwordForgot,
  passwordReset,
  passwordChange,
  publicSettings,
};
```

**Rotas SvelteKit envolvidas:**

- `src/routes/(auth)/login/+page.svelte`
- `src/routes/(auth)/register/+page.svelte`
- `src/routes/(auth)/activation/request/+page.svelte`
- `src/routes/(auth)/activation/pending/+page.svelte`
- `src/routes/(auth)/activation/confirm/+page.svelte`
- `src/routes/(auth)/forgot-password/+page.svelte`
- `src/routes/(auth)/reset-password/+page.svelte`
- `src/routes/(auth)/change-password/+page.svelte`
- `src/routes/(auth)/tenant-select/+page.svelte`
- `src/routes/(auth)/awaiting/+page.svelte`
- `src/routes/(auth)/+layout.server.ts`
- `src/routes/(app)/+layout.server.ts`

## Constraints & Rules

1. Endpoints publicos de auth usam `skipAuth: true` e `skipTenant: true`.
2. `GET /auth/me` e `GET /auth/me/tenants` nao exigem `X-Tenant-ID`.
3. Erros de auth exibem `error.message` do envelope padrao via toast.
4. `awaiting_assignment: true` ou ausencia de tokens no login levam para `/awaiting` sem chamar `/auth/me`, exceto superadmin que segue para selecao de tenant global.
5. Token de ativacao e reset vem por query string `?token=`.
6. `registration_enabled === false` oculta link de cadastro e bloqueia `/register`.
7. `platform_name` aparece no titulo/layout das telas publicas.
8. Validacoes de rotas autenticadas acontecem via SSR (`+layout.server.ts`/`+page.server.ts`) antes do render, usando cookies.
9. Cadastro novo redireciona para `/activation/pending`, pois o envio do e-mail de ativacao acontece automaticamente no backend.

## Implementation Checklist

- [x] Criar `frontend/src/lib/api/auth.ts` com todos os metodos de auth.
- [x] Criar `frontend/src/routes/(auth)/+layout.server.ts`:
  - [x] Chamar `/system-settings/public`.
  - [x] Expor `platform_name` e `registration_enabled`.
- [x] Implementar `frontend/src/routes/(auth)/login/+page.svelte`:
  - [x] Form com email e password.
  - [x] Submit faz login, salva tokens, carrega profile/memberships e redireciona.
  - [x] Login com `awaiting_assignment=true` nao salva token nulo e nao chama `/auth/me`.
  - [x] Erros usam toast e envelope padrao da API.
  - [x] Link de registro respeita `registration_enabled`.
  - [x] Link para forgot-password.
- [x] Implementar `frontend/src/routes/(auth)/register/+page.svelte`.
- [x] Proteger `/register` com `+page.server.ts` quando registro estiver desabilitado.
- [x] Implementar request e confirm de ativacao.
- [x] Implementar tela pending de ativacao apos registro automatico.
- [x] Implementar forgot-password e reset-password.
- [x] Implementar change-password com guard SSR.
- [x] Implementar guard SSR em `frontend/src/routes/(app)/+layout.server.ts`.
- [x] Proteger `/tenant-select`, `/awaiting` e `/change-password` com `+page.server.ts`.
- [x] Implementar logout completo no app shell, tenant-select e awaiting.
- [x] Criar pagina `/awaiting` para usuarios sem tenant.

## Acceptance Criteria

- [x] Login bem-sucedido armazena tokens, hidrata `authStore.user` e `authStore.memberships`, e redireciona corretamente.
- [x] Login 200 sem tenant assignment redireciona para `/awaiting` sem disparar request autenticado invalido.
- [x] Login de superadmin sem memberships reais redireciona para `/tenant-select`, onde tenants globais sao carregados por permissao superadmin.
- [x] Login com credenciais invalidas exibe erro sem redirecionar.
- [x] Logout revoga refresh token quando possivel, limpa stores/localStorage/cookies e redireciona para `/login`.
- [x] Reload autenticado reidrata estado pelo SSR sem renderizar rota protegida antes do redirect.
- [x] Ativacao de conta via link de email confirma com sucesso via `?token=`.
- [x] Registro novo leva para tela de pendencia de confirmacao, nao para o formulario de reenvio.
- [x] Reset de senha via link de email funciona com `?token=` na URL.
- [x] `registration_enabled === false` oculta o link de cadastro e bloqueia `/register`.
- [x] `platform_name` aparece no titulo/layout das paginas publicas.

## Verification

```bash
cd frontend
npm run check
npm run test:unit
```

## Risks & Rollback

- **Risco**: cookies nao sincronizados com stores podem quebrar SSR apos login. Mitigacao: `authStore.setTokens()` e `tenantStore.setActiveTenant()` espelham valores em cookies.
- **Risco**: backend indisponivel no layout publico pode bloquear login. Mitigacao: fallback local para `GENAI` e `registration_enabled=true`.
- **Rollback**: reverter arquivos de rotas auth e helper SSR; backend nao e alterado por esta task.

## Execution Log

- `[2026-05-08 00:00]`: Task criada.
- `[2026-05-08 00:45]`: Fluxos de login, registro, ativacao, recuperacao, reset, troca de senha e logout passaram a usar toast e mensagens parseadas do envelope padrao da API.
- `[2026-05-08 01:10]`: Guards de rotas autenticadas movidos para SSR com cookies (`+layout.server.ts` e `+page.server.ts`), eliminando render client-side antes do redirect.
- `[2026-05-08 12:57]`: Public settings carregados no layout SSR de auth, endpoints publicos ignoram tenant header, registro respeita `registration_enabled` e TASK-067 concluida apos `npm run check` e `npm run test:unit`.
- `[2026-05-08 13:20]`: Corrigido fluxo pos-registro: `/auth/register` envia e-mail automaticamente no backend, frontend redireciona para `/activation/pending`; `/activation/request?email=...` redireciona para pending e o reenvio fica como acao secundaria.
- `[2026-05-08 20:50]`: Corrigido fluxo de login com `awaiting_assignment=true`: frontend nao grava `access_token=null`, nao chama `/auth/me` sem bearer token, e carrega `/auth/me/tenants` apos login com token para obter slug/nome do tenant antes do redirect.
- `[2026-05-08 21:00]`: Login de superadmin sem memberships reais passou a redirecionar para `/tenant-select`; a selecao carrega tenants globais via `/superadmin/tenants` e usa role virtual `superadmin`.
