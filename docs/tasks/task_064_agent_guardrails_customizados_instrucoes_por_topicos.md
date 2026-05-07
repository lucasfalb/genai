# Task: TASK-064 - Agent Guardrails Customizados e Instrucoes por Topicos

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-064 |
| **Group** | ENGINE |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_05_prompts.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Codex |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-08 |

## Context

O agente LangGraph base ja monta prompt com core prompt, skills, tools e constraints fixas. Para um produto multitenant, usuarios precisam configurar instrucoes por topicos e guardrails customizados sem depender de alteracao de codigo.

Os guardrails existentes continuam no `PromptSanitizer`, mas agora a configuracao editavel da instancia entra como blocos estruturados, versionaveis, auditaveis e validados antes da execucao.

## Objectives

- [x] Permitir que cada instancia de agente tenha instrucoes estruturadas por topicos.
- [x] Permitir guardrails customizados por instancia, com categorias como seguranca, comportamento, compliance, tom de voz e limites de ferramenta.
- [x] Definir schema persistido para instrucoes e guardrails sem quebrar `core_prompt`.
- [x] Atualizar `PromptBuilder` para montar prompt a partir de blocos ordenados e tipados.
- [x] Atualizar `PromptSanitizer` para validar guardrails customizados e impedir dados sensiveis.
- [x] Registrar mudancas em audit/version tenant-scoped com actor context.
- [x] Expor contratos API/Bruno para listar e atualizar configuracao de instrucoes/guardrails.

## Non-Goals

- [x] Implementar execucao real de tools/skills.
- [x] Implementar RAG ou handoff completo.
- [x] Criar UI visual de prompt builder.
- [x] Criar motor de policy externo ou DSL complexa.

## Stage Boundaries

Esta task pertence ao Stage 05 Prompt Runtime. Ela altera contrato de agente, prompt builder, sanitizer, endpoints tenant-scoped e documentacao Swagger/Bruno. Nao implementa stages de RAG, canais ou handoff completo.

## Dependencies

- TASK-032
- TASK-036
- TASK-037
- TASK-038
- TASK-040

## Inputs & Contracts

- **Inputs**: `agent_instances.core_prompt`, `agent_instances.instruction_blocks`, `agent_instances.guardrails`, metadata de skills/tools e linked agents.
- **Outputs**: `SystemPrompt` montado com secoes ordenadas, guardrails validados, audit/version tenant-scoped e response API envelope.
- **Migration**: `20260508_0010_agent_prompt_config.py`.
- **Endpoints**:
  - `GET /api/v1/tenant/instances/{instance_id}/prompt-config`
  - `PUT /api/v1/tenant/instances/{instance_id}/prompt-config`
- **Schemas**:
  - `AgentInstructionBlock`: `id`, `topic`, `title`, `content`, `priority`, `is_enabled`
  - `AgentGuardrail`: `id`, `category`, `rule`, `severity`, `is_enabled`, `metadata`
  - `AgentPromptConfigRequest`
  - `AgentPromptConfigResponse`

## Constraints & Rules

1. Toda configuracao e tenant-scoped e respeita RBAC de administracao de instancia.
2. Superadmin pode alterar agente de qualquer tenant sem virar membro visivel, mas a mudanca aparece em audit/version do tenant.
3. Guardrails customizados nao podem conter segredos, tokens, API keys ou dados sensiveis.
4. Topicos sao ordenados por `priority`, `topic` e `id` para evitar prompt drift.
5. `PromptSanitizer` bloqueia configuracao com campos ou valores sensiveis antes de cache/execucao.
6. Guardrails usam severidade controlada: `info`, `warning`, `critical` e `blocking`.
7. Alterar instrucoes ou guardrails invalida `PromptCache` e `ToolMetadataCache`.
8. Responses usam envelope `ApiResponse` e nao retornam dados sensiveis.
9. Bruno e OpenAPI cobrem os endpoints criados.
10. Tests cobrem montagem do prompt, validacao, auditoria/versionamento e invalidacao de cache.

## Implementation Checklist

- [x] Criar migration para `instruction_blocks` e `guardrails` em `agent_instances`.
- [x] Definir Pydantic schemas de request/response para instruction blocks e guardrails.
- [x] Atualizar repository de agent instances para persistir e retornar essas configuracoes.
- [x] Criar endpoints tenant-scoped para prompt config da instancia.
- [x] Atualizar `PromptBuilder` para montar secoes por topico em ordem deterministica.
- [x] Atualizar `PromptSanitizer` para validar guardrails customizados.
- [x] Invalidar `PromptCache` quando instrucoes ou guardrails mudarem.
- [x] Registrar audit/version tenant-scoped em toda mutacao.
- [x] Atualizar Bruno e OpenAPI.
- [x] Criar testes unitarios e integrados do fluxo completo.

## Acceptance Criteria

- [x] Tenant admin consegue criar e atualizar instrucoes por topico de uma instancia.
- [x] Tenant admin consegue criar e atualizar guardrails customizados de uma instancia.
- [x] Prompt final inclui core prompt, topicos, skills/tools, guardrails e constraints em ordem previsivel.
- [x] Guardrails com dados sensiveis sao rejeitados antes da execucao.
- [x] Mudancas invalidam `PromptCache`.
- [x] Mudancas aparecem em audit/version do tenant com actor context correto.
- [x] Superadmin consegue alterar configuracao do agente sem aparecer como tenant member.
- [x] OpenAPI e Bruno cobrem os endpoints.
- [x] Testes cobrem prompt build, sanitizer, RBAC, audit/version e cache invalidation.

## Verification

```bash
cd backend
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\python -m pytest tests/test_stage_05_agent_instances.py tests/test_stage_05_prompt_runtime.py tests/test_prompt_sanitizer.py -q
cd ..
backend\.venv\Scripts\python scripts\validate_openapi.py
python scripts\validate_tasks.py
```

## Risks & Rollback

- **Risks**: guardrails customizados podem gerar prompts contraditorios, extensos ou impossiveis de seguir; schema muito solto pode dificultar UI e validacao.
- **Rollback**: manter `core_prompt` como fonte principal e ignorar blocos/guardrails desabilitados ate corrigir validadores; migration pode remover as colunas JSONB.

## Execution Log

- `[2026-05-07 22:20]`: Task criada para evoluir agente base com guardrails customizados e instrucoes por topicos antes da verificacao E2E final.
- `[2026-05-08 00:00]`: Migration, schemas, endpoints, PromptBuilder, PromptSanitizer, Bruno e testes implementados.
