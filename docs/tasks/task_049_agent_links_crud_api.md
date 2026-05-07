# Task: TASK-049 - agent_links CRUD API Tenant-Scoped

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-049 |
| **Group** | HANDOFF |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_07_handoff.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Tenant admins precisam configurar quais instancias podem transferir para quais outras e com que descricao. Esta task expoe o CRUD de `agent_links` sob o contexto de uma instancia de origem.

## Objectives

- [ ] Criar `APIRouter` em `api/v1/tenant_agent_links.py` com prefix `/tenant/instances/{instance_id}/links`.
- [ ] `GET /tenant/instances/{instance_id}/links` — listar vinculos da instancia.
- [ ] `POST /tenant/instances/{instance_id}/links` — criar vinculo.
- [ ] `PATCH /tenant/instances/{instance_id}/links/{link_id}` — atualizar descricao ou modo.
- [ ] `DELETE /tenant/instances/{instance_id}/links/{link_id}` — remover vinculo.
- [ ] Invalidar `ToolMetadataCache` e `PromptCache` da instancia apos mutacao.
- [ ] Adicionar requests Bruno em `genai-endpoints/TenantAgentLinks/`.

## Non-Goals

- Tool fantasma no bootstrap (TASK-050).
- Router classifier (TASK-052).

## Stage Boundaries

Apenas CRUD de vinculos. Nenhuma logica de execucao de hand-off.

## Dependencies

- TASK-048 (repositorio de agent_links)
- TASK-040 (PromptCache.invalidate — deve ser chamada em mutacoes)

## Inputs & Contracts

- **Inputs**: `target_instance_id`, `transfer_tool_name`, `trigger_description`, `transfer_mode`.
- **Outputs**: `AgentLinkResponse(id, source_instance_id, target_instance_id, transfer_tool_name, trigger_description, transfer_mode, is_enabled)`.
- **Schemas**: `AgentLinkCreateRequest`, `AgentLinkUpdateRequest`, `AgentLinkResponse`, `ApiResponse[T]`.

## Constraints & Rules

1. Requer Bearer token, `X-Tenant-ID` e permissao `MANAGE_AGENT_INSTANCES`.
2. `source_instance_id` e `target_instance_id` devem pertencer ao mesmo tenant.
3. Auto-link (source == target) e rejeitado com 400.
4. Duplicata (mesmo par) retorna 409.
5. Toda mutacao invalida `ToolMetadataCache` e `PromptCache` da instancia de origem.

## Implementation Checklist

- [ ] Criar schemas em `app/schemas.py`.
- [ ] Criar `api/v1/tenant_agent_links.py` com 4 endpoints.
- [ ] Registrar router em `app/main.py`.
- [ ] Chamar `ToolMetadataCache.invalidate` e `PromptCache.invalidate` em create/update/delete.
- [ ] Adicionar Bruno requests.
- [ ] Testar: create, list, update, delete, auto-link rejeitado, duplicata rejeitada.

## Acceptance Criteria

- [ ] CRUD completo retorna `ApiResponse[AgentLinkResponse]`.
- [ ] Auto-link retorna 400.
- [ ] Duplicata retorna 409.
- [ ] Cache invalidado apos mutacao.

## Verification

```bash
cd backend
pytest tests/test_stage_07_agent_links.py
```

## Risks & Rollback

- **Rollback**: remover router de `app/main.py`.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para CRUD de agent_links.
