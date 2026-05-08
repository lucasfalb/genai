# Task: TASK-066 — API Client Infrastructure

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-066 |
| **Group** | FRONTEND |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_09_frontend.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-08 |
| **Updated At** | 2026-05-08 |

## Context

Toda a comunicacao do frontend com o backend passa por um unico wrapper HTTP tipado. Sem este alicerce nenhum flow de UI pode ser conectado. Esta task cria o cliente HTTP, todos os tipos TypeScript das respostas e requests da API, e os dois stores Svelte 5 centrais (auth e tenant).

## Objectives

- [x] Criar `frontend/src/lib/api/client.ts` — fetch wrapper tipado com injecao automatica de headers.
- [x] Criar `frontend/src/lib/api/types.ts` — interfaces TypeScript para todos os schemas de request/response.
- [x] Criar `frontend/src/lib/stores/auth.svelte.ts` — store Svelte 5 runes de autenticacao.
- [x] Criar `frontend/src/lib/stores/tenant.svelte.ts` — store Svelte 5 runes de tenant ativo.
- [x] Implementar auto-refresh do access token em 401 (uma tentativa antes de redirecionar ao login).
- [x] Implementar persistencia de tokens e tenant ativo em `localStorage`.

## Non-Goals

- Nao implementar UI de nenhuma pagina nesta task.
- Nao implementar funcoes especificas de endpoint (auth.ts, instances.ts etc.) — isso e feito nas tasks seguintes.
- Nao implementar SSE streaming (task_074).

## Stage Boundaries

Apenas infraestrutura de cliente. Nenhuma rota SvelteKit e criada aqui.

## Dependencies

- Nenhuma task anterior de frontend.
- Backend deve estar acessivel localmente (Docker Compose) para testes manuais.

## Inputs & Contracts

**Variaveis de ambiente necessarias:**
- `PUBLIC_API_BASE_URL` (ex: `http://localhost:8000/api/v1`) — lida via `$env/static/public` do SvelteKit.

**Contrato do `client.ts`:**
```typescript
// Funcao principal de request
async function apiRequest<T>(
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE',
  path: string,
  options?: {
    body?: unknown;
    params?: Record<string, string>;
    skipAuth?: boolean;
    skipTenant?: boolean;
  }
): Promise<T>

// Atalhos
export const api = {
  get:    <T>(path: string, params?: Record<string, string>) => apiRequest<T>('GET', path, { params }),
  post:   <T>(path: string, body?: unknown) => apiRequest<T>('POST', path, { body }),
  put:    <T>(path: string, body?: unknown) => apiRequest<T>('PUT', path, { body }),
  patch:  <T>(path: string, body?: unknown) => apiRequest<T>('PATCH', path, { body }),
  del:    <T>(path: string) => apiRequest<T>('DELETE', path),
}
```

**Tipos principais em `types.ts`:**
```typescript
// Envelope padrao do backend
interface ApiResponse<T> {
  status: 'success';
  data: T;
}

interface ApiErrorPayload {
  status: 'error';
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

// Auth
interface LoginRequest { email: string; password: string; }
interface RegisterRequest { email: string; password: string; name: string; }
interface AuthResponse {
  access_token: string; refresh_token: string; token_type: string;
  user_id: string; email: string; awaiting_assignment: boolean;
  memberships: TenantAccessResponse[];
}
interface AuthMeResponse { id: string; email: string; name: string; status: string; is_superadmin: boolean; }
interface TenantAccessResponse {
  tenant_id: string; tenant_slug: string; tenant_name: string; role: string; status: string;
}

// Instancias
interface AgentInstanceResponse {
  id: string; tenant_id: string; name: string; description: string;
  core_prompt: string; model: string; temperature: number;
  status: string; rag_scope: string; created_by: string;
}
interface AgentInstanceCreateRequest {
  name: string; description?: string; core_prompt: string;
  model: string; temperature: number; rag_scope?: string;
}
interface AgentInstanceUpdateRequest {
  name?: string; description?: string; core_prompt?: string;
  model?: string; temperature?: number; rag_scope?: string;
}

// Prompt config
interface AgentInstructionBlock { topic: string; content: string; priority: number; }
interface AgentGuardrail { name: string; rule: string; enabled: boolean; }
interface AgentPromptConfigRequest {
  instruction_blocks: AgentInstructionBlock[];
  guardrails: AgentGuardrail[];
}
interface AgentPromptConfigResponse extends AgentPromptConfigRequest {
  tenant_id: string; instance_id: string;
}

// Registry
interface ToolMetadataResponse { tenant_id: string; instance_id: string; skills: SkillActivation[]; tools: ToolActivation[]; }
interface SkillActivation { skill_slug: string; is_enabled: boolean; config: Record<string, unknown>; }
interface ToolActivation { tool_slug: string; is_enabled: boolean; config: Record<string, unknown>; }
interface ActivationRequest { is_enabled: boolean; config?: Record<string, unknown>; }
interface CredentialResponse { skill_slug: string; secret_ref: string; metadata: Record<string, unknown>; }
interface CredentialRequest { secret_ref: string; metadata?: Record<string, unknown>; }

// Members
interface TenantMemberResponse { user_id: string; email: string; name: string; role: string; status: string; }
interface TenantMemberUpdateRequest { role?: string; status?: string; }

// Invitations
interface TenantInvitationResponse { id: string; email: string; role: string; status: string; expires_at: string; }
interface TenantInvitationCreateRequest { email: string; role: string; }
interface TenantInvitationValidateRequest { token: string; }
interface TenantInvitationPublicResponse {
  tenant_id: string; tenant_name: string; email: string; role: string; status: string; expires_at: string;
}
interface TenantInvitationAcceptRequest { token: string; email: string; name: string; password: string; }
interface TenantInvitationAcceptResponse { user_id: string; tenant_id: string; email: string; role: string; membership_status: string; }

// AI Settings
interface TenantAIConfigResponse {
  tenant_id: string; provider: string; default_model: string;
  enabled: boolean; has_api_key: boolean; configured_by: string;
}
interface TenantAIConfigRequest { provider: string; api_key: string; default_model: string; enabled: boolean; }

// Collections
interface CollectionResponse {
  id: string; tenant_id: string; name: string; description: string;
  indexing_status: string; indexing_progress: number;
  document_count: number; indexed_count: number; failed_count: number;
  last_indexed_at: string | null; created_at: string;
}
interface CollectionCreateRequest { name: string; description?: string; }
interface CollectionUpdateRequest { name?: string; description?: string; }

// System settings
interface PublicSystemSettingsResponse {
  platform_name: string; platform_public_url: string; platform_logo_url: string;
  maintenance_mode: boolean; registration_enabled: boolean; public_settings: Record<string, unknown>;
}

// Chat
interface ChatRequest { message: string; session_id?: string; channel?: string; metadata?: Record<string, unknown>; }

// Superadmin
interface SuperadminTenantCreateRequest { slug: string; name: string; plan: string; status: string; settings?: Record<string, unknown>; }
interface SuperadminTenantResponse { id: string; slug: string; name: string; plan: string; status: string; settings: Record<string, unknown>; }
interface SuperadminUserResponse { id: string; email: string; name: string; status: string; is_superadmin: boolean; }
interface SkillDefinitionRequest { slug: string; name: string; description: string; config_schema: Record<string, unknown>; }
interface ToolDefinitionRequest { slug: string; name: string; description: string; config_schema: Record<string, unknown>; }
interface EmailTemplateRequest { template_key: string; subject: string; body: string; variables_schema: Record<string, unknown>; }
interface SystemSettingsUpdateRequest { [key: string]: unknown; }
```

**Store `auth.svelte.ts`:**
```typescript
// Svelte 5 runes
const authStore = {
  user: $state<AuthMeResponse | null>(null),
  accessToken: $state<string | null>(null),
  refreshToken: $state<string | null>(null),
  memberships: $state<TenantAccessResponse[]>([]),
  isAuthenticated: $derived(/* accessToken != null */),
}
```

**Store `tenant.svelte.ts`:**
```typescript
const tenantStore = {
  activeTenantId: $state<string | null>(null),
  activeTenantSlug: $state<string | null>(null),
  activeTenantName: $state<string | null>(null),
  role: $state<string | null>(null),
}
```

## Constraints & Rules

1. `client.ts` NAO pode ser importado dentro de layouts `+layout.server.ts` — apenas em componentes client-side e `+page.ts` (client load functions).
2. Header `Authorization: Bearer {accessToken}` e injetado automaticamente se `authStore.accessToken` estiver preenchido, exceto quando `skipAuth: true`.
3. Header `X-Tenant-ID` e injetado automaticamente se `tenantStore.activeTenantId` estiver preenchido.
4. Em caso de 401: chamar `POST /auth/refresh` uma vez com o `refreshToken`. Se falhar, limpar stores e redirecionar para `/login`.
5. `localStorage` keys: `genai_access_token`, `genai_refresh_token`, `genai_tenant_id`.
6. Os stores tambem espelham tokens/tenant ativo em cookies para suportar guards SSR das rotas autenticadas.
7. Erros HTTP devem ser lancados como `ApiError extends Error` com `status: number` e `message: string`.
8. Endpoints publicos devem poder passar `skipTenant: true` para evitar envio indevido de `X-Tenant-ID`.
9. O client deve mapear o envelope padrao de erro do backend (`status: error`, `error.code`, `error.message`) para `ApiError`.
10. Svelte 5 runes: arquivos de store devem ter extensao `.svelte.ts` para habilitar contexto de runes.

## Implementation Checklist

- [x] Criar `frontend/src/lib/api/types.ts` com TODOS os tipos listados em Inputs & Contracts.
- [x] Criar `frontend/src/lib/api/client.ts`:
  - [x] Ler `PUBLIC_API_BASE_URL` de `$env/static/public`.
  - [x] Funcao `apiRequest<T>()` com method, path, body, params.
  - [x] Injetar `Authorization` header se `authStore.accessToken` presente.
  - [x] Injetar `X-Tenant-ID` header se `tenantStore.activeTenantId` presente.
  - [x] Permitir `skipTenant` em chamadas publicas.
  - [x] Deserializar envelope `ApiResponse<T>` e retornar `.data`.
  - [x] Lancar `ApiError` em respostas com `status !== 'success'` ou HTTP >= 400.
  - [x] Mapear `error.message` do backend para `ApiError.message`.
  - [x] Interceptar 401: chamar `refreshAccessToken()`, atualizar store/localStorage, retry original request.
  - [x] Se refresh falhar: chamar `clearAuthAndRedirect()` para `/login`.
  - [x] Exportar objeto `api` com atalhos `get`, `post`, `put`, `patch`, `del`.
- [x] Criar `frontend/src/lib/stores/auth.svelte.ts`:
  - [x] Campos: `user`, `accessToken`, `refreshToken`, `memberships` com `$state`.
  - [x] Derivado `isAuthenticated` com `$derived`.
  - [x] Funcao `loadFromLocalStorage()` para hidratar na inicializacao.
  - [x] Funcao `setTokens(access, refresh)` que salva em store + localStorage/cookies.
  - [x] Funcao `clearAuth()` que limpa store + localStorage/cookies.
- [x] Criar `frontend/src/lib/stores/tenant.svelte.ts`:
  - [x] Campos: `activeTenantId`, `activeTenantSlug`, `activeTenantName`, `role` com `$state`.
  - [x] Funcao `setActiveTenant(tenant: TenantAccessResponse)` que atualiza store + localStorage/cookies.
  - [x] Funcao `clearTenant()` que limpa store + localStorage/cookies.
- [x] Escrever testes unitarios (vitest) para `client.ts`:
  - [x] Teste: injecao de Authorization header.
  - [x] Teste: injecao de X-Tenant-ID header.
  - [x] Teste: retry automatico em 401 com refresh bem-sucedido.
  - [x] Teste: redirect em 401 com refresh falhando.
  - [x] Teste: lancamento de ApiError em resposta de erro do backend.

## Acceptance Criteria

- [x] `apiRequest()` injeta `Authorization` e `X-Tenant-ID` automaticamente a partir dos stores.
- [x] Em 401, o cliente tenta refresh e reenvia o request original exatamente uma vez.
- [x] Se o refresh falhar, `clearAuth()` e chamada e o usuario e redirecionado a `/login`.
- [x] Todos os tipos de `types.ts` compilam sem erros TypeScript.
- [x] Stores inicializam corretamente com dados do `localStorage` ao carregar a aplicacao.
- [x] `ApiError` contem `status` (HTTP code) e `message` (mensagem do backend).
- [x] Nenhuma chamada `fetch()` direta fora de `client.ts` em codigo client-side; guards SSR usam helper server-side proprio.

## Verification

```bash
cd frontend
npm run check        # TypeScript type check
npm run test:unit    # vitest unit tests
```

## Risks & Rollback

- **Risco**: Svelte 5 runes em `.svelte.ts` fora de componentes pode ter comportamento inesperado em SSR. Mitigacao: usar `browser` guard do SvelteKit antes de acessar `localStorage`.
- **Risco**: Circular dependency entre `client.ts` e stores. Mitigacao: stores nao importam `client.ts`; `client.ts` importa stores apenas para leitura.
- **Rollback**: Como e infraestrutura nova sem alterar backend, rollback e simplesmente remover os arquivos criados.

## Execution Log

- `[2026-05-08 00:00]`: Task criada.
- `[2026-05-08 00:45]`: Client atualizado para parsear envelope padrao de sucesso/erro, expor `getErrorMessage()` e suportar `skipTenant` em endpoints publicos.
- `[2026-05-08 12:55]`: Vitest adicionado, testes unitarios do client criados e TASK-066 concluida apos `npm run test:unit` e `npm run check`.
