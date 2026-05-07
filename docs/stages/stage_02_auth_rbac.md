# Stage 02 — Auth, JWT e RBAC

_Fonte canônica: [`../platform_technical_spec.md`](../platform_technical_spec.md). Este stage reorganiza o conteúdo técnico sem substituir a especificação completa._

## Objetivo

Implementar autenticação, emissão de tokens, seleção de tenant e autorização por papel antes de expor APIs administrativas ou canais de consumo.

## 3. Sistema de Autenticação e RBAC

### Fluxo de autenticação

JWT com refresh tokens. O access token representa a identidade global; o contexto de tenant é selecionado por header `X-Tenant-ID`.

```
POST /auth/register
  → Cria user status="pending"
  → Envia email de verificação
  → Aguarda convite ou atribuição de role

POST /auth/login
  → Valida credenciais
  → Se sem memberships → retorna flag "awaiting_assignment"
  → Se tem membership ativa → emite JWT + refresh token
```

### Roles e permissões

| Permissão | Superadmin | Tenant Admin | Member | Viewer |
|-----------|:---:|:---:|:---:|:---:|
| Gerir tenants e users globais | ✓ | — | — | — |
| Criar/editar instâncias de agente | — | ✓ | — | — |
| Ativar/desativar skills e tools | — | ✓ | — | — |
| Vincular agentes (configurar hand-off) | — | ✓ | — | — |
| Configurar canais | — | ✓ | ✓ | — |
| Upload de documentos RAG | — | ✓ | ✓ | — |
| Convidar membros | — | ✓ | — | — |
| Ver logs e traces | — | ✓ | ✓ | ✓ |
| Interagir com agentes | — | ✓ | ✓ | ✓ |

### Middleware de autorização

```python
# dependencies/auth.py

async def get_tenant_context(request: Request, user = Depends(get_current_user)) -> TenantContext:
    tenant_id = request.headers.get("X-Tenant-ID")
    if not tenant_id:
        raise HTTPException(400, "X-Tenant-ID header obrigatório")

    cache_key = f"membership:{user.sub}:{tenant_id}"
    cached = await redis.get(cache_key)
    if cached:
        return TenantContext.model_validate_json(cached)

    membership = await db.get_active_membership(user.sub, tenant_id)
    if not membership:
        raise HTTPException(403, "Sem acesso a este tenant")

    ctx = TenantContext(tenant_id=tenant_id, user_id=user.sub, role=membership.role)
    await redis.setex(cache_key, 300, ctx.model_dump_json())
    return ctx
```

---

### Regra de superadmin, membership e auditoria

`users.is_superadmin = true` representa o responsavel global da plataforma. O superadmin tem permissao total e pode operar qualquer tenant sem registro em `memberships`.

Essa regra nao significa anonimato nas trilhas do tenant. Em qualquer acao feita pelo superadmin dentro do escopo de um tenant, a aplicacao deve persistir:

- `tenant_id` do tenant afetado.
- `user_id` do superadmin.
- `actor_type = 'superadmin'`.
- `actor_role = 'superadmin'`.
- acao, recurso, `resource_id`, metadata sanitizada e versao quando aplicavel.

Listagens de membros do tenant devem consultar `memberships` e excluir `users.is_superadmin = true`. Logs, auditoria e historico de versoes devem consultar `audit_logs` e `resource_versions`, onde o superadmin deve aparecer normalmente como ator da mudanca.

## Lacunas Encaminhadas ao Stage 05

O Stage 02 implementa a fundacao de auth/RBAC. Os workflows completos abaixo foram explicitamente movidos para `docs/stages/stage_05_base_multitenant_workflows.md` e `docs/tasks/stage_05_tasks.md`:

- Ativacao de conta por email.
- Recovery, reset e change de senha.
- `GET /auth/me`, `GET /auth/me/tenants` e logout.
- Convites de tenant e aceite.
- Administracao de membros por tenant.
- CRUD superadmin de tenants/users.
- Auditoria/versionamento/cache para mutacoes administrativas base.
