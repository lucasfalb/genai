# Task: TASK-076 - Frontend Route Topology

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-076 |
| **Group** | FRONTEND |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_09_frontend.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-08 |
| **Updated At** | 2026-05-08 |

## Context

O frontend precisa separar claramente a area operacional de cada tenant da area global de superadmin. A area do usuario deve usar `/app/{tenantSlug}` para deixar explicito qual tenant esta sendo gerido. A area global de administracao da plataforma deve usar `/admin` e exigir superadmin no SSR.

## Objectives

- [x] Mover rotas tenant-scoped para `/app/{tenantSlug}`.
- [x] Manter redirects de compatibilidade para URLs antigas como `/dashboard`, `/instances` e `/settings`.
- [x] Validar no SSR que o `{tenantSlug}` da URL pertence ao usuario autenticado ou e acessivel por superadmin global.
- [x] Criar rota `/admin` com guard SSR para `is_superadmin`.
- [x] Atualizar navegacao, tenant selector e redirects de login/tenant-select para a nova topologia.

## Non-Goals

- Nao implementar o painel superadmin completo - isso permanece em TASK-075.
- Nao alterar contratos de API backend.
- Nao criar novos endpoints.

## Stage Boundaries

Apenas topologia de rotas e guards SSR do frontend.

## Dependencies

- TASK-067 - auth SSR e cookies.
- TASK-068 - contexto de tenant ativo.

## Inputs & Contracts

**Rotas tenant-scoped:**

```text
/app/{tenantSlug}/dashboard
/app/{tenantSlug}/instances
/app/{tenantSlug}/instances/new
/app/{tenantSlug}/instances/{id}
/app/{tenantSlug}/settings/members
/app/{tenantSlug}/settings/invitations
/app/{tenantSlug}/settings/credentials
```

**Rotas globais:**

```text
/admin
```

**Redirects de compatibilidade:**

```text
/dashboard -> /app/{activeTenantSlug}/dashboard
/instances -> /app/{activeTenantSlug}/instances
/instances/* -> /app/{activeTenantSlug}/instances/*
/settings -> /app/{activeTenantSlug}/settings/members
/settings/* -> /app/{activeTenantSlug}/settings/*
```

## Constraints & Rules

1. O segmento `{tenantSlug}` deve corresponder a um tenant associado ao usuario, exceto superadmin que pode acessar qualquer tenant existente.
2. Se a URL usar `tenant_id`, o SSR normaliza para `tenant_slug`.
3. Se o tenant da URL nao pertence ao usuario, redirecionar para `/tenant-select`.
4. A troca de tenant pelo selector deve navegar para `/app/{tenantSlug}/dashboard`.
5. `/admin` nunca usa `X-Tenant-ID` como contexto visual; e area global de plataforma.
6. `/admin` deve bloquear usuarios sem `is_superadmin` antes do render.

## Implementation Checklist

- [x] Mover `dashboard`, `instances` e `settings` para `frontend/src/routes/(app)/app/[tenant]/`.
- [x] Atualizar `frontend/src/routes/(app)/+layout.server.ts` para validar `params.tenant`.
- [x] Criar helpers `tenantPath()` e `tenantBaseFromPath()`.
- [x] Atualizar links do app shell para prefixar `/app/{tenantSlug}`.
- [x] Atualizar tenant selector e redirects de login/awaiting/tenant-select.
- [x] Carregar tenants globais para superadmin em `/tenant-select` e `/app/{tenantSlug}` usando role virtual `superadmin`.
- [x] Simplificar aside tenant-scoped para Agents, Observability, Configuration e Members.
- [x] Redirecionar `/app/{tenantSlug}` e `/app/{tenantSlug}/dashboard` para `/instances`.
- [x] Criar redirects legados para `/dashboard`, `/instances` e `/settings`.
- [x] Criar `/admin` com guard SSR de superadmin.

## Acceptance Criteria

- [x] Usuario autenticado com tenant ativo acessa `/app/{tenantSlug}/dashboard`.
- [x] URLs antigas tenant-scoped redirecionam para `/app/{tenantSlug}`.
- [x] Tenant selector troca tenant e atualiza a URL para o slug correto.
- [x] URL com tenant invalido redireciona para `/tenant-select`.
- [x] `/admin` so renderiza para `is_superadmin === true`.
- [x] Superadmin acessa `/app/{tenantSlug}` sem precisar membership explicita no tenant.
- [x] Aside nao exibe Skills, Tools, Knowledge ou Invitations como links separados.

## Verification

```bash
cd frontend
npm run check
npm run test:unit
cd ..
python scripts/validate_tasks.py
```

## Risks & Rollback

- **Risco**: links hardcoded para rotas antigas podem aparecer em novas telas. Mitigacao: usar `tenantPath()` ou `tenantBaseFromPath()` ao criar links tenant-scoped.
- **Risco**: bookmarks antigos quebrarem. Mitigacao: redirects legados para as superficies ja implementadas.
- **Rollback**: mover rotas de volta para `(app)` raiz e remover guards/redirects adicionados.

## Execution Log

- `[2026-05-08 13:25]`: Rotas tenant-scoped migradas para `/app/{tenantSlug}` e `/admin` criado com guard SSR de superadmin.
- `[2026-05-08 13:25]`: Verificado com `npm run check` e `npm run test:unit`.
- `[2026-05-08 21:00]`: Regra de superadmin refinada: `/app/{tenantSlug}` e `/tenant-select` carregam tenants de `/superadmin/tenants` com role virtual `superadmin`, mantendo memberships reais inalteradas.
- `[2026-05-08 20:35]`: Topologia visual do app simplificada: menu lateral agora tem Agents, Observability, Configuration e Members; `/dashboard` redireciona para Agents e Invitations fica dentro de Members.
