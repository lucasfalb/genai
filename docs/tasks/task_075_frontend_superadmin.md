# Task: TASK-075 - Superadmin Panel UI

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-075 |
| **Group** | FRONTEND |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_09_frontend.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | MEDIUM |
| **Owner** | Unassigned |
| **Created At** | 2026-05-08 |
| **Updated At** | 2026-05-08 |

## Context

Superadmins precisam de um painel dedicado para gerenciar tenants, usuarios, registry de skills/tools, templates de email e configuracoes globais da plataforma. A rota frontend canonica e `/admin/*`; os endpoints backend continuam no prefixo API `/superadmin/*`.

## Objectives

- [x] Criar `frontend/src/lib/api/superadmin.ts` com funcoes tipadas para os 16 endpoints superadmin.
- [x] Completar route guard `/admin/+layout.server.ts` - apenas `is_superadmin === true`.
- [x] Implementar `/admin/tenants` - listagem + criacao + edicao de tenants.
- [x] Implementar `/admin/users` - listagem + edicao de usuarios.
- [x] Implementar `/admin/registry/skills` e `/admin/registry/tools` - listagem + edicao de definicoes.
- [x] Implementar `/admin/email-templates` - listagem + edicao de templates.
- [x] Implementar `/admin/settings` - formulario de configuracoes de sistema.

## Non-Goals

- Nao implementar criacao de superadmin via UI (feita via seeds/CLI).
- Nao implementar delecao de tenants (operacao critica - sem UI para isso).
- Nao implementar logs de auditoria detalhados nesta task.

## Stage Boundaries

Apenas UI do painel superadmin. Sem novos endpoints no backend.

## Dependencies

- TASK-067 - `authStore.user.is_superadmin` disponivel apos hidratacao do auth.
- TASK-076 - topologia `/admin` e guard SSR base criados.

## Inputs & Contracts

**Arquivo `frontend/src/lib/api/superadmin.ts`** (implementado com 16 metodos):

```typescript
import { api } from '$lib/api/client';
import type {
  SuperadminTenantCreateRequest, SuperadminTenantResponse,
  SuperadminTenantUpdateRequest, SuperadminUserResponse, SuperadminUserUpdateRequest,
  SkillDefinitionResponse, SkillDefinitionRequest, ToolDefinitionResponse, ToolDefinitionRequest,
  EmailTemplateResponse, EmailTemplateRequest, SystemSettingsResponse, SystemSettingsUpdateRequest
} from '$lib/api/types';

const SA = { skipTenant: true } as const;

export const superadminApi = {
  listTenants:    () => api.get<SuperadminTenantResponse[]>('/superadmin/tenants', SA),
  createTenant:   (body: SuperadminTenantCreateRequest) => api.post<SuperadminTenantResponse>('/superadmin/tenants', body, SA),
  getTenant:      (id: string) => api.get<SuperadminTenantResponse>(`/superadmin/tenants/${id}`, SA),
  updateTenant:   (id: string, body: SuperadminTenantUpdateRequest) =>
    api.put<SuperadminTenantResponse>(`/superadmin/tenants/${id}`, body, SA),
  listUsers:      () => api.get<SuperadminUserResponse[]>('/superadmin/users', SA),
  getUser:        (id: string) => api.get<SuperadminUserResponse>(`/superadmin/users/${id}`, SA),
  updateUser:     (id: string, body: SuperadminUserUpdateRequest) =>
    api.put<SuperadminUserResponse>(`/superadmin/users/${id}`, body, SA),
  listSkills:     () => api.get<SkillDefinitionResponse[]>('/superadmin/registry/skills', SA),
  saveSkill:      (slug: string, body: SkillDefinitionRequest) =>
    api.put<SkillDefinitionResponse>(`/superadmin/registry/skills/${slug}`, body, SA),
  listTools:      () => api.get<ToolDefinitionResponse[]>('/superadmin/registry/tools', SA),
  saveTool:       (slug: string, body: ToolDefinitionRequest) =>
    api.put<ToolDefinitionResponse>(`/superadmin/registry/tools/${slug}`, body, SA),
  listTemplates:  () => api.get<EmailTemplateResponse[]>('/superadmin/email-templates', SA),
  getTemplate:    (slug: string) => api.get<EmailTemplateResponse>(`/superadmin/email-templates/${slug}`, SA),
  saveTemplate:   (slug: string, body: EmailTemplateRequest) =>
    api.put<EmailTemplateResponse>(`/superadmin/email-templates/${slug}`, body, SA),
  getSettings:    () => api.get<SystemSettingsResponse>('/superadmin/system-settings', SA),
  updateSettings: (body: SystemSettingsUpdateRequest) =>
    api.put<SystemSettingsResponse>('/superadmin/system-settings', body, SA),
};
```

**Helper SSR adicionado em `frontend/src/lib/server/api.ts`:**

```typescript
export async function superadminBackendRequest<T>(
  fetcher: typeof fetch,
  path: string,
  session: { accessToken: string },
  init: RequestInit = {}
): Promise<T>
// Mesmo que tenantBackendRequest mas sem X-Tenant-ID
```

**Frontend routes:**

- `/admin/tenants`
- `/admin/tenants/members`
- `/admin/tenants/{tenantId}/members`
- `/admin/users`
- `/admin/registry/skills`
- `/admin/registry/tools`
- `/admin/email-templates`
- `/admin/settings`

## Constraints & Rules

1. Route guard obrigatorio: qualquer rota `/admin/*` redireciona para `/tenant-select` se `is_superadmin !== true`.
2. Painel superadmin NAO injeta `X-Tenant-ID` como contexto visual; superadmins operam fora do contexto de tenant.
3. Edicao de `is_superadmin` deve exibir aviso de seguranca antes de confirmar.
4. `slug` de tenant e imutavel apos criacao - exibir readonly no formulario de edicao.
5. JSON de skills/tools/templates/settings deve ser validado sintaticamente antes do submit.
6. Template de email: `variables_schema` define variaveis como `{{ variable_name }}` - listar acima do campo body.
7. Superadmin nao deve ver menu de tenant ativo no painel `/admin`.
8. Paginacao ou scroll infinito recomendado para listas longas - MVP pode usar listagem simples.

## Implementation Checklist

- [x] Criar `frontend/src/lib/api/superadmin.ts` com todos os metodos.
- [x] Adicionar `superadminBackendRequest` em `frontend/src/lib/server/api.ts`.
- [x] Completar `frontend/src/routes/(admin)/admin/+layout.server.ts`.
- [x] Criar `frontend/src/routes/(admin)/admin/+layout.svelte`:
  - [x] Sidebar de navegacao: Overview, Tenants, Usuarios, Skills, Tools, Email Templates, Configuracoes.
  - [x] Header: ShieldAlert icon + "Superadmin" + link para voltar ao app.
- [x] Criar SSR loaders `+page.server.ts` para cada rota.
- [x] Criar `frontend/src/routes/(admin)/admin/tenants/+page.svelte`.
- [x] Corrigir layout `/admin/*` para usar o mesmo padrao visual e componente de sidebar de `/app/*`.
- [x] Criar seletor `/admin/tenants/members` para escolher tenant antes da gestao de membros.
- [x] Corrigir `/admin/tenants/{tenantId}/members` para carregar usuarios via SSR e adicionar membros por combobox.
- [x] Redirecionar superadmin sem tenant para `/admin` em vez de `/awaiting`.
- [x] Incluir superadmins ativos no combobox de usuarios para adicionar membro ao tenant.
- [x] Criar `frontend/src/routes/(admin)/admin/users/+page.svelte`.
- [x] Criar `frontend/src/routes/(admin)/admin/registry/skills/+page.svelte`.
- [x] Criar `frontend/src/routes/(admin)/admin/registry/tools/+page.svelte`.
- [x] Criar `frontend/src/routes/(admin)/admin/email-templates/+page.svelte`.
- [x] Criar `frontend/src/routes/(admin)/admin/settings/+page.svelte`.

## Acceptance Criteria

- [x] Rota `/admin/*` redireciona usuarios nao-superadmin para `/tenant-select`.
- [x] Listagem de tenants exibe todos com status badges corretos.
- [x] Criacao de tenant persiste no backend e adiciona a lista.
- [x] Edicao de tenant persiste campos editaveis (nao altera slug).
- [x] Listagem de usuarios com busca local por email/nome funciona.
- [x] Toggle is_superadmin exibe aviso de seguranca antes de confirmar.
- [x] Skills e tools podem ser editadas com JSON valido.
- [x] Email templates podem ser editados e salvos.
- [x] Configuracoes de sistema carregam e podem ser salvas.
- [x] `/admin/*` usa sidebar, header e densidade visual compativeis com `/app/*`.
- [x] `/admin/tenants` exibe acao explicita para abrir detalhes do tenant.
- [x] Adicao/edicao de membros envia `role` e `status` como string, nunca como array.
- [x] Superadmin adiciona tenant member selecionando usuario existente em combobox carregado do backend.
- [x] Superadmin autenticado sem membership acessa painel `/admin` sem precisar ser atribuido a tenant.
- [x] Modal de membros lista usuarios ativos da plataforma, inclusive `is_superadmin === true`.

## Verification

```bash
cd frontend
npm run check
# Teste manual: acessar /admin como superadmin e como usuario normal (deve redirecionar)
# Testar criacao de tenant, edicao de usuario, edicao de skill
```

## Risks & Rollback

- **Risco**: Formulario de settings dinamico pode ter campos de tipos desconhecidos. **Resolvido**: settings page tem campos explicitamente tipados por secao (Platform, SMTP, AI Config); password fields usam `type="password"`.
- **Risco**: Acesso indevido por usuario que adulterou estado local com `is_superadmin: true`. **Mitigacao**: SSR guard em `+layout.server.ts` consulta `parent()` que chama `/auth/me`; todos endpoints backend aplicam `require_superadmin` independentemente.
- **Risco**: Classe Tailwind com opacidade (`bg-blue-500/5`) em diretiva `class:` causa parse error Svelte. **Resolvido**: usar ternario em `class=""` string: `class="{cond ? 'bg-blue-500/5' : ''}"`.
- **Rollback**: Remover grupo de rotas `/admin/` - sem alteracoes no backend.

## Execution Log

- `[2026-05-08 00:00]`: Task criada.
- `[2026-05-08 15:30]`: Correcao de conformidade visual e funcional: `/admin/*` passou a usar `Sidebar.Provider/Root/Inset` como `/app/*`; `/admin/tenants` ganhou CTA explicito para detalhes; `/admin/tenants/members` ganhou seletor de tenant; `/admin/tenants/{tenantId}/members` passou a carregar usuarios via SSR e adicionar membros por combobox, usando selects nativos para garantir payload `role/status` como string.
- `[2026-05-08 19:45]`: Fluxo de superadmin ajustado: login, `/tenant-select`, `/awaiting` e `/app` redirecionam superadmin sem membership para `/admin`; combobox de adicionar membro passou a incluir usuarios superadmin ativos.
- `[2026-05-08 13:25]`: Topologia atualizada para frontend `/admin/*`, mantendo API backend `/superadmin/*`.
- `[2026-05-08 14:00]`: Implementacao completa — 15 arquivos criados/modificados. `superadminBackendRequest` adicionado ao server api; `superadmin.ts` cliente com 16 metodos; layout com sidebar; 6 page.server.ts loaders; 6 paginas Svelte. Erro de parse Svelte com `class:bg-blue-500/5` corrigido em todos os arquivos. Erro TypeScript no skills page (tuple tipagem) corrigido com bind:value explicitamente. `npm run check`: 0 errors.
