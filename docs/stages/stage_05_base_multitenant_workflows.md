# Stage 05 - Base Multitenant Workflows

_Fonte canonica: [`../platform_technical_spec.md`](../platform_technical_spec.md). Este stage fecha lacunas de base operacional antes de avancar para prompt runtime, RAG, handoff completo e canais._

## Objetivo

Completar os workflows fundamentais de um SaaS multi-tenant: ciclo de vida de conta, convites, membros, tenants, instancias de agentes, auditoria/versionamento e contratos de API/Bruno.

## Escopo

Este stage existe porque os stages 01-04 entregaram a fundacao tecnica, mas ainda deixaram fluxos operacionais incompletos:

- Registro cria usuario `pending`, mas nao ha ativacao de conta.
- Templates de email existem, mas nao ha emissao/consumo de tokens transacionais.
- Tabela `invitations` existe, mas nao ha endpoints de convite e aceite.
- Superadmin tem permissao global, mas ainda faltam endpoints de gestao de tenants/users.
- Tenant admin tem RBAC, mas ainda faltam APIs de membros e instancias.
- Auditoria/versionamento existe, mas precisa cobrir mutacoes administrativas base.
- A collection Bruno deve acompanhar todos os endpoints criados.

## Workflows Obrigatorios

### 1. Account lifecycle

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/activation/request`
- `POST /api/v1/auth/activation/confirm`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/me/tenants`
- `POST /api/v1/auth/logout`

Usuarios comuns so devem receber tokens finais quando estiverem ativos e possuirem membership ativa ou quando forem superadmin.

### 2. Password lifecycle

- `POST /api/v1/auth/password/forgot`
- `POST /api/v1/auth/password/reset`
- `POST /api/v1/auth/password/change`

Tokens de reset devem ser hashados no banco, expirar, ser single-use e nunca aparecer em logs.

### 3. Tenant invitation lifecycle

- Tenant admin e superadmin podem criar convites.
- Convites geram token single-use e usam template `tenant_invitation`.
- Aceite cria ou associa usuario, cria membership ativa e invalida caches de membership.
- Superadmin pode executar acao em qualquer tenant, mas nao vira membro visivel.

### 4. Tenant and member administration

- Superadmin gerencia tenants e usuarios globais.
- Tenant admin gerencia membros do proprio tenant.
- Listagem de membros nao retorna superadmin.
- Mudancas de role/status entram em `audit_logs` e `resource_versions`.

### 5. Agent instance administration

- Tenant admin cria/lista/edita/arquiva instancias.
- Instancias respeitam `tenant_id`, RLS e RBAC.
- Mudancas administrativas invalidam caches afetados.

### 6. Contract and workflow coverage

- Cada endpoint novo deve ter OpenAPI valido.
- Cada endpoint novo deve ter request em `genai-endpoints/`.
- Cada endpoint JSON deve usar envelope padrao de sucesso/erro para facilitar consumo no frontend:
  - sucesso: `{"status":"success","message":...,"data":...,"meta":{...}}`
  - erro: `{"status":"error","error":{"code":...,"message":...}}`, com `details` somente quando houver dados estruturados de diagnostico.
- Workflows principais devem ter testes de integracao.

## Regras de Superadmin

O superadmin e ator global com controle total por tenant, mas nao e membership visivel. Qualquer alteracao tenant-scoped feita por superadmin deve persistir `tenant_id`, `user_id`, `actor_type = 'superadmin'`, `actor_role = 'superadmin'` em auditoria e versoes quando aplicavel.

## Fora de Escopo

- Provedor real de email em producao.
- Frontend/dashboard.
- SSO/SAML/OAuth social.
- Billing e planos.
- Prompt runtime, RAG, handoff completo e canais externos.

## Validacao

```bash
docker compose up -d postgres redis qdrant
cd backend
alembic upgrade head
pytest
cd ..
backend\.venv\Scripts\python scripts\validate_openapi.py
python scripts\validate_tasks.py
```

## Implementacao Parcial

- TASK-025 revisada e endurecida com `tenant_id` opcional em tokens transacionais, constraints de tipo/status, consumo filtravel por tipo e rejeicao de payload sensivel em email events.
- TASK-026 implementa ativacao de conta: registro enfileira email de ativacao, `/auth/activation/request` reemite token com resposta neutra e `/auth/activation/confirm` ativa o usuario com token single-use.
- TASK-027 implementa password lifecycle: `/auth/password/forgot` emite resposta neutra e token single-use, `/auth/password/reset` troca senha e revoga refresh tokens, e `/auth/password/change` exige Bearer token e senha atual.
- TASK-028 implementa introspeccao de auth: `/auth/me` retorna identidade global segura, `/auth/me/tenants` retorna memberships reais sem membership sintetica para superadmin, e `/auth/logout` revoga refresh tokens.
- TASK-029 implementa administracao superadmin de tenants e usuarios: CRUD operacional de tenants, list/get/update de usuarios globais, bloqueio de auto-demote/auto-suspensao e auditoria/versionamento em mutacoes.
- TASK-035 padroniza respostas JSON com `ApiResponse[T]` em sucesso, `ApiErrorResponse` em erro e validacao OpenAPI para impedir regressao de contrato.
- Login e refresh agora bloqueiam usuarios com `status != 'active'`.
