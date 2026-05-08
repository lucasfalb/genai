# Stage 09 Tasks - Frontend Integration

| ID | Task | Status | Priority | Depends On |
| :--- | :--- | :--- | :--- | :--- |
| TASK-066 | [API Client Infrastructure](task_066_frontend_api_client_infrastructure.md) | COMPLETED | CRITICAL | - |
| TASK-067 | [Auth Flows API Wiring](task_067_frontend_auth_flows.md) | COMPLETED | CRITICAL | TASK-066 |
| TASK-068 | [Tenant Context & Invitation Flows](task_068_frontend_tenant_context_invitations.md) | COMPLETED | HIGH | TASK-067 |
| TASK-069 | [Agent Instances Management UI](task_069_frontend_agent_instances.md) | COMPLETED | HIGH | TASK-068 |
| TASK-070 | [Registry Management UI](task_070_frontend_registry.md) | COMPLETED | HIGH | TASK-069 |
| TASK-071 | [Members & Invitations Team Management UI](task_071_frontend_members_invitations.md) | COMPLETED | MEDIUM | TASK-068 |
| TASK-072 | [Tenant AI Settings UI](task_072_frontend_tenant_ai_settings.md) | COMPLETED | MEDIUM | TASK-068 |
| TASK-073 | [Collections (RAG) Management UI](task_073_frontend_collections.md) | COMPLETED | MEDIUM | TASK-068 |
| TASK-074 | [Agent Chat Interface (SSE)](task_074_frontend_agent_chat.md) | PENDING | HIGH | TASK-069 |
| TASK-075 | [Superadmin Panel UI](task_075_frontend_superadmin.md) | COMPLETED | MEDIUM | TASK-067 |
| TASK-076 | [Frontend Route Topology](task_076_frontend_route_topology.md) | COMPLETED | HIGH | TASK-067 |

## Scope

Estas tasks cobrem o Stage 09 definido em `docs/stages/stage_09_frontend.md`: implementar toda a camada de frontend SvelteKit 5 conectada aos 59 endpoints da API REST do GenAI Platform backend.

## Implementation Order

1. Criar infraestrutura de cliente HTTP tipado e stores Svelte 5.
2. Fechar todos os flows de autenticacao com wiring real aos endpoints.
3. Implementar selecao e contexto de tenant, e flow publico de convites.
4. Implementar CRUD de instancias de agente e aba de prompt config.
5. Implementar gestao de registry (skills/tools) dentro do detalhe da instancia.
6. Implementar gestao de membros e convites por tenant.
7. Implementar formulario de configuracao AI do tenant.
8. Implementar gestao de colecoes RAG com status de indexacao.
9. Implementar interface de chat com streaming SSE.
10. Implementar painel superadmin completo.

## Notes

- Nenhum endpoint novo no backend e criado neste stage.
- Todas as chamadas passam pelo `client.ts` centralizado com injecao automatica de headers.
- Svelte 5 runes (`$state`) sao obrigatorios — nao usar `writable()` legado.
- Toda rota tenant-scoped vive sob `/app/{tenantSlug}` e exige `activeTenantId`; redirecionar se ausente.
- Rotas `/admin/*` exigem `is_superadmin === true` no SSR guard.
- Menu tenant-scoped foi simplificado para Agents, Observability, Configuration e Members; collections ficam acessiveis pela secao Knowledge do detalhe de Agent e por `/app/{tenantSlug}/collections`.
- A experiencia de criacao/detalhe de Agents carrega defaults publicos de `system_settings.public_settings.agent_ui`, incluindo modelos, templates e painel lateral de teste.
