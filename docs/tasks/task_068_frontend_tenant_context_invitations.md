# Task: TASK-068 - Tenant Context & Invitation Flows

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-068 |
| **Group** | FRONTEND |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_09_frontend.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-08 |
| **Updated At** | 2026-05-08 |

## Context

Com usuario autenticado, o frontend precisa estabelecer o tenant ativo antes de qualquer chamada tenant-scoped. Esta task implementa selecao e persistencia de tenant, guard SSR de contexto ativo e fluxo publico de aceite de convite sem autenticacao previa.

## Objectives

- [x] Implementar pagina de selecao de tenant baseada em memberships hidratadas via SSR.
- [x] Ao selecionar tenant, atualizar `tenantStore` e persistir `genai_tenant_id` em localStorage e cookie.
- [x] Implementar guard SSR no app shell para exigir tenant ativo antes de renderizar rotas protegidas.
- [x] Implementar flow publico de convite: validate -> form accept -> POST accept.
- [x] Criar funcoes tipadas de convite publico em `frontend/src/lib/api/invitations.ts`.
- [x] Criar alias `/accept-invitation` para compatibilidade com links gerados pelo backend.

## Non-Goals

- Nao implementar CRUD autenticado de convites; isso pertence a TASK-071.
- Nao implementar criacao de novo tenant via frontend.
- Nao implementar administracao de membros.

## Stage Boundaries

Apenas contexto de tenant, selecao de tenant e aceite publico de convite. Nenhum CRUD tenant-scoped administrativo e concluido aqui.

## Dependencies

- TASK-067 - Auth flows e hidratacao SSR de sessao.

## Inputs & Contracts

**Funcoes publicas em `frontend/src/lib/api/invitations.ts`:**

```typescript
export const invitationsPublicApi = {
  validate: (body) => api.post('/invitations/validate', body, { skipAuth: true, skipTenant: true }),
  accept: (body) => api.post('/invitations/accept', body, { skipAuth: true, skipTenant: true }),
};
```

**Rotas e componentes:**

- `frontend/src/routes/(auth)/tenant-select/+page.svelte`
- `frontend/src/routes/(auth)/tenant-select/+page.server.ts`
- `frontend/src/routes/(auth)/invite/+page.svelte`
- `frontend/src/routes/(auth)/accept-invitation/+page.server.ts`
- `frontend/src/lib/components/tenant-selector.svelte`
- `frontend/src/routes/(app)/+layout.server.ts`
- `frontend/src/routes/(app)/+layout.svelte`

## Constraints & Rules

1. `POST /invitations/validate` e `POST /invitations/accept` nao requerem autenticacao e nao enviam `X-Tenant-ID`.
2. O token do convite vem por query string e nao e salvo em storage.
3. Aceite de convite redireciona o usuario para login.
4. `tenantStore.setActiveTenant()` salva `genai_tenant_id` em localStorage e cookie.
5. `/tenant-select` redireciona para `/app/{tenantSlug}/dashboard` se houver tenant unico ou tenant ativo valido.
6. Usuarios sem memberships vao para `/awaiting`, nao para lista vazia de tenants.
7. O backend gera `/accept-invitation?token=...`; o frontend redireciona esta rota para `/invite?token=...`.

## Implementation Checklist

- [x] Criar `frontend/src/lib/api/invitations.ts` com `validate` e `accept`.
- [x] Garantir `skipAuth: true` e `skipTenant: true` nos endpoints publicos de convite.
- [x] Criar `frontend/src/routes/(auth)/invite/+page.svelte`:
  - [x] Ler `token` de query string.
  - [x] Validar convite ao montar.
  - [x] Exibir tenant, role e email.
  - [x] Exibir erro amigavel para token invalido ou expirado.
  - [x] Enviar aceite com nome, email e senha.
  - [x] Exibir sucesso com link para login.
- [x] Criar alias `frontend/src/routes/(auth)/accept-invitation/+page.server.ts`.
- [x] Implementar `frontend/src/routes/(auth)/tenant-select/+page.svelte`:
  - [x] Exibir lista de memberships com nome do tenant e role.
  - [x] Ao clicar, chamar `tenantStore.setActiveTenant()` e ir para dashboard.
  - [x] Fazer logout completo a partir da tela.
- [x] Atualizar app shell para usar memberships reais no `TenantSelector`, sem dados mockados.
- [x] Atualizar `tenantStore.svelte.ts` com persistencia localStorage/cookie e reidratacao por memberships.
- [x] Manter guard SSR no `(app)/+layout.server.ts` para tenant ativo antes do render.

## Acceptance Criteria

- [x] Usuarios com tenant unico sao redirecionados diretamente ao dashboard.
- [x] Usuarios com multiplos tenants veem a lista e podem selecionar.
- [x] Reload da pagina mantem tenant ativo via cookie/localStorage.
- [x] Convite valido exibe nome do tenant e role antes de aceite.
- [x] Convite expirado/invalido exibe mensagem de erro sem crashar.
- [x] Apos aceitar convite, usuario recebe confirmacao e link para login.
- [x] `X-Tenant-ID` e enviado em chamadas tenant-scoped apos selecao de tenant.
- [x] Links `/accept-invitation?token=...` do backend funcionam no frontend.

## Verification

```bash
cd frontend
npm run check
npm run test:unit
```

## Risks & Rollback

- **Risco**: cookie e localStorage divergirem no tenant ativo. Mitigacao: `setActiveTenant()` grava ambos e SSR valida membership antes de aceitar cookie.
- **Risco**: link antigo/alternativo de convite quebrar. Mitigacao: alias `/accept-invitation` preserva token e redireciona para `/invite`.
- **Rollback**: reverter rotas de convite, `TenantSelector` e alteracoes de `invitations.ts`.

## Execution Log

- `[2026-05-08 00:00]`: Task criada.
- `[2026-05-08 13:00]`: Tenant selector conectado a memberships reais, endpoints publicos de convite ajustados para nao enviar tenant header, alias `/accept-invitation` criado e TASK-068 concluida apos `npm run check` e `npm run test:unit`.
