# Task: TASK-064 - Agent Guardrails Customizados e Instrucoes por Topicos

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-064 |
| **Group** | ENGINE |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_05_prompts.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

O agente LangGraph base ja monta prompt com core prompt, skills, tools e constraints fixas. Isso e pouco para um produto multitenant: usuarios precisam configurar instrucoes por topicos e guardrails customizados sem depender de alteracao de codigo.

Hoje os guardrails existentes estao concentrados no `PromptSanitizer`, principalmente em validacao de densidade, duplicidade e conflitos de instrucao. A proxima evolucao deve separar o contrato de instrucao do agente em blocos editaveis, versionaveis e validaveis antes da execucao.

## Objectives

- [ ] Permitir que cada instancia de agente tenha instrucoes estruturadas por topicos.
- [ ] Permitir guardrails customizados por instancia, com categorias como seguranca, comportamento, compliance, tom de voz e limites de ferramenta.
- [ ] Definir schema persistido para instrucoes e guardrails sem quebrar `core_prompt`.
- [ ] Atualizar `PromptBuilder` para montar prompt a partir de blocos ordenados e tipados.
- [ ] Atualizar `PromptSanitizer` para validar guardrails customizados, conflitos e densidade por bloco.
- [ ] Registrar mudancas em audit/version tenant-scoped com actor context.
- [ ] Expor contratos API/Bruno para criar, atualizar e listar configuracao de instrucoes/guardrails.

## Non-Goals

- Implementar execucao real de tools/skills.
- Implementar RAG ou handoff completo.
- Criar UI visual de prompt builder.
- Criar motor de policy externo ou DSL complexa.

## Stage Boundaries

Esta task pertence ao Stage 05 Prompt Runtime. Ela altera contrato de agente, prompt builder, sanitizer, endpoints tenant-scoped e documentacao Swagger/Bruno. Nao deve implementar stages de RAG, canais ou handoff completo.

## Dependencies

- TASK-032
- TASK-036
- TASK-037
- TASK-038

## Inputs & Contracts

- **Inputs**: `agent_instances.core_prompt`, novos blocos de instrucoes, novos guardrails customizados, metadata de skills/tools e linked agents.
- **Outputs**: `SystemPrompt` montado com secoes ordenadas, guardrails validados, audit/version tenant-scoped e response API com contrato redigido.
- **Schemas propostos**:
  - `agent_instances.instruction_blocks JSONB`
  - `agent_instances.guardrails JSONB`
  - `AgentInstructionBlock`: `id`, `topic`, `title`, `content`, `priority`, `is_enabled`
  - `AgentGuardrail`: `id`, `category`, `rule`, `severity`, `is_enabled`, `metadata`

## Constraints & Rules

1. Toda configuracao deve ser tenant-scoped e respeitar RBAC de administracao de instancia.
2. Superadmin pode alterar agente de qualquer tenant sem virar membro visivel, mas a mudanca deve aparecer em audit/version do tenant.
3. Guardrails customizados nao podem conter segredos, tokens, API keys ou dados sensiveis.
4. Topicos devem ser ordenaveis e deterministas para evitar prompt drift.
5. `PromptSanitizer` deve bloquear conflitos explicitos entre guardrails customizados e constraints fixas.
6. Guardrails devem ter severidade controlada, por exemplo `info`, `warning`, `critical` e `blocking`.
7. Alterar instrucoes ou guardrails deve invalidar `PromptCache`.
8. Responses devem usar envelope `ApiResponse` e nunca retornar dados sensiveis.
9. Bruno e OpenAPI devem cobrir todos os endpoints criados ou alterados.
10. Tests devem cobrir montagem do prompt, validacao, auditoria/versionamento e invalidacao de cache.

## Implementation Checklist

- [ ] Criar migration para `instruction_blocks` e `guardrails` em `agent_instances` ou tabela dedicada tenant-scoped.
- [ ] Definir Pydantic schemas de request/response para instruction blocks e guardrails.
- [ ] Atualizar repository de agent instances para persistir e retornar essas configuracoes.
- [ ] Atualizar endpoints tenant-scoped de agente ou criar endpoints dedicados para instrucoes/guardrails.
- [ ] Atualizar `PromptBuilder` para montar secoes por topico em ordem deterministica.
- [ ] Atualizar `PromptSanitizer` para validar guardrails customizados por bloco.
- [ ] Invalidar `PromptCache` quando instrucoes ou guardrails mudarem.
- [ ] Registrar audit/version tenant-scoped em toda mutacao.
- [ ] Atualizar Bruno e OpenAPI.
- [ ] Criar testes unitarios e integrados do fluxo completo.

## Acceptance Criteria

- [ ] Tenant admin consegue criar e atualizar instrucoes por topico de uma instancia.
- [ ] Tenant admin consegue criar e atualizar guardrails customizados de uma instancia.
- [ ] Prompt final inclui core prompt, topicos, skills/tools, guardrails e constraints em ordem previsivel.
- [ ] Guardrails conflitantes ou perigosos sao rejeitados antes da execucao.
- [ ] Mudancas invalidam `PromptCache`.
- [ ] Mudancas aparecem em audit/version do tenant com actor context correto.
- [ ] Superadmin consegue alterar configuracao do agente sem aparecer como tenant member.
- [ ] OpenAPI e Bruno cobrem os endpoints.
- [ ] Testes cobrem prompt build, sanitizer, RBAC, audit/version e cache invalidation.

## Verification

```bash
cd backend
alembic upgrade head
pytest tests/test_stage_05_agent_instances.py
pytest tests/test_stage_05_prompt_runtime.py
pytest tests/test_prompt_sanitizer.py
cd ..
backend\.venv\Scripts\python scripts\validate_openapi.py
python scripts\validate_tasks.py
```

## Risks & Rollback

- **Risks**: guardrails customizados podem gerar prompts contraditorios, extensos ou impossiveis de seguir; schema muito solto pode dificultar UI e validacao.
- **Rollback**: manter `core_prompt` como fonte principal e ignorar blocos/guardrails desabilitados ate corrigir validadores.

## Execution Log

- `[2026-05-07 22:20]`: Task criada para evoluir agente base com guardrails customizados e instrucoes por topicos antes da verificacao E2E final.
