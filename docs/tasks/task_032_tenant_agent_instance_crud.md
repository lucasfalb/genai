# Task: TASK-032 - Tenant Agent Instance CRUD

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-032 |
| **Group** | REGISTRY |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_05_base_multitenant_workflows.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Skills/tools podem ser ativadas em instancias existentes, mas ainda nao ha API base para tenant admins criarem e administrarem instancias de agentes.

## Objectives

- [ ] Criar CRUD tenant-scoped de `agent_instances`.
- [ ] Expor listagem e detalhes por tenant.
- [ ] Permitir arquivar/desarquivar instancia sem apagar dados historicos.
- [ ] Invalidar caches de metadata quando instancia mudar.

## Non-Goals

- PromptBuilder completo do Stage 06 futuro.
- UI de criacao de instancia.

## Stage Boundaries

Esta task cobre administracao operacional de instancias, prerequisito para workflows de prompt/RAG/canais.

## Dependencies

- TASK-015
- TASK-030

## Inputs & Contracts

- **Inputs**: `X-Tenant-ID`, nome, core prompt, modelo/provider opcional e status.
- **Outputs**: instancia tenant-scoped sem dados cross-tenant.
- **Schemas**: Pydantic requests/responses de agent instance.

## Constraints & Rules

1. Queries devem exigir `tenant_id` e respeitar RLS.
2. Apenas roles com permissao de gerenciar instancias podem mutar.
3. Arquivamento nao deve apagar sessoes ou mensagens.
4. Superadmin pode mutar qualquer tenant com auditoria.

## Implementation Checklist

- [ ] Criar repository de agent instances.
- [ ] Criar endpoints tenant-scoped de CRUD.
- [ ] Testar isolamento cross-tenant.
- [ ] Integrar audit/version e cache invalidation.
- [ ] Atualizar Bruno e OpenAPI.

## Acceptance Criteria

- [ ] Tenant admin cria, lista, atualiza e arquiva instancias do proprio tenant.
- [ ] Viewer nao consegue mutar instancias.
- [ ] Cross-tenant access retorna 404 ou 403 conforme contrato.
- [ ] Mudancas aparecem em audit/version quando aplicavel.

## Verification

```bash
cd backend
pytest tests/test_stage_05_agent_instances.py
```

## Risks & Rollback

- **Risks**: endpoint de instancia pode abrir acesso cross-tenant a configuracoes.
- **Rollback**: desabilitar roteador de instancias e manter ativacao de registry bloqueada.

## Execution Log

- `[2026-05-07 15:40]`: Task criada para cobrir CRUD de instancias antes de prompts/RAG/canais.
