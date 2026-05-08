# Task: TASK-071 - Members & Invitations Team Management UI

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-071 |
| **Group** | FRONTEND |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_09_frontend.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | MEDIUM |
| **Owner** | Unassigned |
| **Created At** | 2026-05-08 |
| **Updated At** | 2026-05-08 |

## Context

Tenants precisam gerenciar seus membros e convites via dashboard. Esta task implementa as paginas de gestao de equipe: lista de membros com edicao de role/status, e gestao de convites pendentes (criar, reenviar, cancelar). Cobre os 3 endpoints de members e 4 endpoints de invitations autenticados.

## Objectives

- [x] Criar `frontend/src/lib/api/members.ts` com funcoes tipadas para os 3 endpoints de members.
- [x] Complementar `frontend/src/lib/api/invitations.ts` com funcoes autenticadas para os 4 endpoints de invitations tenant-scoped.
- [x] Implementar pagina `/settings/members` com tabela de membros, inline role/status change e botao de remocao.
- [x] Integrar convites dentro de `/settings/members`, removendo Invitations do menu lateral.

## Non-Goals

- Nao implementar o flow publico de aceitacao de convite - isso foi feito em TASK-068.
- Nao implementar edicao de perfil do proprio usuario (TASK-067 cobre change-password).
- Nao implementar criacao de usuarios diretamente - apenas convites.

## Stage Boundaries

Apenas gestao de membros e convites autenticados. Nenhum endpoint publico aqui.

## Dependencies

- TASK-068 - contexto de tenant ativo disponivel, guard de autenticacao funcional.

## Inputs & Contracts

**Arquivo `frontend/src/lib/api/members.ts`:**
```typescript
import { api } from '$lib/api/client';
import type { TenantMemberResponse, TenantMemberUpdateRequest } from '$lib/api/types';

export const membersApi = {
  list:   () => api.get<TenantMemberResponse[]>('/tenant/members'),
  update: (userId: string, body: TenantMemberUpdateRequest) =>
    api.patch<TenantMemberResponse>(`/tenant/members/${userId}`, body),
  remove: (userId: string) => api.del<void>(`/tenant/members/${userId}`),
};
```

**Funcoes autenticadas em `frontend/src/lib/api/invitations.ts`:**
```typescript
import type { TenantInvitationResponse, TenantInvitationCreateRequest } from '$lib/api/types';

export const invitationsApi = {
  list:   () => api.get<TenantInvitationResponse[]>('/tenant/invitations'),
  create: (body: TenantInvitationCreateRequest) =>
    api.post<TenantInvitationResponse>('/tenant/invitations', body),
  cancel: (id: string) => api.del<void>(`/tenant/invitations/${id}`),
  resend: (id: string) => api.post<TenantInvitationResponse>(`/tenant/invitations/${id}/resend`),
};
```

**Pagina `/settings/members/+page.svelte`:**
- Tabela de membros: avatar/iniciais, nome, email, role badge, status badge, acoes.
- Role badge: `tenant_admin` azul, `member` cinza, `viewer` ciano.
- Status badge: `active` verde, `suspended` vermelho, `pending` amarelo.
- Edicao inline de role/status com dropdowns.
- Botao "Remover" com confirmacao usando `membersApi.remove(userId)`.
- Nao permitir auto-remocao do usuario logado.
- Permissao RBAC e verificada pelo backend; o frontend apenas melhora UX.

**Pagina `/settings/invitations/+page.svelte`:**
- Form de convite: campo email, select de role, botao "Invite".
- Submit: `invitationsApi.create({ email, role })` e atualizacao da lista local.
- Lista de convites: email, role, status, expires_at, acoes.
- Status badge: `pending` amarelo, `accepted` verde, `expired` vermelho.
- Botao "Resend" usando `invitationsApi.resend(id)`.
- Botao "Cancel" com confirmacao usando `invitationsApi.cancel(id)`.

## Constraints & Rules

1. Um membro nao pode remover a si mesmo - ocultar/desabilitar botao para o usuario logado.
2. Roles disponiveis para atribuicao conforme backend: `tenant_admin`, `member`, `viewer`.
3. Convite duplicado para o mesmo email deve retornar erro 409 - exibir mensagem clara.
4. Convites expirados devem ser distinguiveis visualmente (badge vermelho, texto "Expired").
5. `expires_at` deve ser formatado como data legivel.
6. O `PATCH /tenant/members/{user_id}` suporta `role` e `status` separadamente - enviar apenas o campo alterado.
7. Permissao RBAC e verificada no backend; frontend pode ocultar opcoes com base no contexto para melhor UX, mas o backend e a fonte de verdade.

## Implementation Checklist

- [x] Criar `frontend/src/lib/api/members.ts` com metodos `list`, `update`, `remove`.
- [x] Adicionar funcoes autenticadas em `frontend/src/lib/api/invitations.ts`: `list`, `create`, `cancel`, `resend`.
- [x] Criar `frontend/src/routes/(app)/settings/members/+page.server.ts`:
  - [x] Carregar membros via SSR.
- [x] Criar `frontend/src/routes/(app)/settings/members/+page.svelte`:
  - [x] Tabela de membros com colunas: nome, email, role badge, status badge, acoes.
  - [x] Select de role inline por linha, exceto para o proprio usuario e roles protegidos.
- [x] Incorporar form e listagem de convites dentro da pagina de members.
  - [x] Ao mudar role: `membersApi.update(userId, { role })` e atualizar linha.
  - [x] Botao "Remover" com dialogo de confirmacao e remocao da lista.
  - [x] Feedback toast de sucesso/erro.
- [x] Criar `frontend/src/routes/(app)/settings/invitations/+page.server.ts`:
  - [x] Carregar convites via SSR.
- [x] Criar `frontend/src/routes/(app)/settings/invitations/+page.svelte`:
  - [x] Form de convite: input email, select role (`tenant_admin` | `member` | `viewer`), botao Invite.
  - [x] Submit: `invitationsApi.create()` limpa form e adiciona a lista.
  - [x] Erro 409 exibe "Email already invited or already a tenant member."
  - [x] Tabela de convites: email, role, status badge, expires_at formatado, acoes.
  - [x] Botao "Resend" chama `invitationsApi.resend(id)` e exibe toast.
  - [x] Botao "Cancel" com confirmacao chama `invitationsApi.cancel(id)` e remove da lista.
- [x] Criar componente `frontend/src/lib/components/RoleBadge.svelte` (reutilizavel).
- [x] Criar componente `frontend/src/lib/components/StatusBadge.svelte` (reutilizavel).

## Acceptance Criteria

- [x] Lista de membros exibe todos os membros do tenant ativo.
- [x] Alteracao de role persiste no backend e atualiza a UI imediatamente.
- [x] Remocao de membro exige confirmacao e remove da lista.
- [x] Usuario logado nao pode se auto-remover.
- [x] Criacao de convite exibe confirmacao e adiciona convite a lista.
- [x] Convite duplicado exibe mensagem de erro amigavel.
- [x] Reenvio de convite exibe toast de confirmacao.
- [x] `/settings/invitations` redireciona para `/settings/members`.
- [x] Cancelamento de convite exige confirmacao e remove da lista.
- [x] Datas de expiracao sao exibidas em formato legivel.

## Verification

```bash
cd frontend
npm run check
npm run test:unit
cd ..
python scripts/validate_tasks.py
# Teste manual: convidar membro, alterar role, remover membro, cancelar convite
```

## Risks & Rollback

- **Risco**: Endpoint retorna membros incluindo o proprio usuario. Mitigacao: guard frontend para bloquear auto-remocao comparando `userId` com o usuario logado.
- **Risco**: Roles protegidos podem aparecer na lista. Mitigacao: desabilitar select/remocao para `owner` e `superadmin`.
- **Rollback**: Remover arquivos criados - sem alteracoes no backend.

## Execution Log

- `[2026-05-08 00:00]`: Task criada.
- `[2026-05-08 13:17]`: Implementadas paginas SSR `/settings/members` e `/settings/invitations`, cliente members e componentes de badge.
- `[2026-05-08 13:17]`: Contrato de roles ajustado ao backend atual: `tenant_admin`, `member`, `viewer`.
- `[2026-05-08 13:17]`: Verificado com `npm run check` e `npm run test:unit`.
- `[2026-05-08 20:35]`: Invitations foi incorporado em Members; a rota antiga `/settings/invitations` virou redirect para `/settings/members` e o aside nao exibe mais Invitations.
