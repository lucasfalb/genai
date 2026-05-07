# Task: TASK-039 - LLM Node e Provider Integration

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-039 |
| **Group** | ENGINE |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_05_prompts.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Codex |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

O `llm_node` do grafo LangGraph precisava deixar de ser placeholder e executar chamada real ao LLM usando o `SystemPrompt` montado pelo `PromptBuilder`, os schemas de tools/skills/hand-offs e a configuracao AI resolvida para o tenant.

A arquitetura atual nao usa `OPENAI_API_KEY` do `.env` como fonte principal. A resolucao correta e:

1. Configuracao AI do tenant em colunas de `tenants`, quando `ai_enabled=true` e a chave existe.
2. Fallback global em `system_settings`.
3. `OPENAI_API_KEY` do `.env` somente como fallback local/development.

## Objectives

- [x] Centralizar chamada ao provider em `engine/llm_client.py`, sem expor credenciais em logs ou estado serializado.
- [x] Reescrever `llm_node` para chamar LLM real com `system_prompt`, historico e `tool_schemas` do `AgentState`.
- [x] Resolver `ai_provider` e `ai_api_key` pelo `AIProviderResolver` no bootstrap, respeitando tenant -> system_settings -> fallback dev.
- [x] Tratar resposta de texto livre em `final_response`.
- [x] Tratar tool calls em `pending_tool_calls`.
- [x] Configurar `model` da instancia no cliente, com fallback `gpt-4.1-mini`.
- [x] Testar com mock de provider: texto livre, tool call e falhas de contrato.

## Non-Goals

- [x] Implementar providers adicionais alem de OpenAI.
- [x] Implementar streaming token-a-token do provider.
- [x] Executar tools reais no `dispatch_node`.
- [x] Implementar RAG no `rag_node`.

## Stage Boundaries

Substitui o LLM placeholder por integracao real com provider OpenAI e conecta o bootstrap ao resolver de provider. Nao cria novos endpoints e nao implementa executor de tools/skills.

## Dependencies

- TASK-037
- TASK-023
- TASK-061
- TASK-062

## Inputs & Contracts

- **Inputs**: `AgentState.messages`, `AgentState.system_prompt`, `AgentState.tool_schemas`, `AgentState.model`, `AgentState.temperature`, `AgentState.ai_provider`, `AgentState.ai_api_key`.
- **Outputs**: `AgentState` com `final_response` (str) OU `pending_tool_calls` (list[dict]).
- **Provider config**: `AIProviderResolver.resolve(tenant_id)` retorna `ResolvedAIConfig(provider, api_key, default_model)`.
- **Tool call contract**: `pending_tool_calls` segue formato `[{"name": str, "id": str, "arguments": dict}]`.
- **Endpoint contract**: falha de provider ou provider ausente no chat retorna `HTTP 502` pelo handler do endpoint.

## Constraints & Rules

1. Chaves de API nunca aparecem em logs, responses, traces ou testes de snapshot.
2. Configuracao de producao vem do tenant ou de `system_settings`; `.env` e fallback dev apenas.
3. `model` vem de `agent_instances.model`; fallback para `gpt-4.1-mini`.
4. `temperature` vem de `agent_instances.temperature`; fallback para `0.2`.
5. Tool call com argumentos JSON invalidos deve falhar de forma explicita.
6. Provider nao suportado deve falhar como erro de provider, sem fallback silencioso para outro provider.

## Implementation Checklist

- [x] Validar dependencia `openai` no `backend/pyproject.toml`.
- [x] Criar `engine/llm_client.py` com cliente OpenAI async e parsing padronizado.
- [x] Reescrever `llm_node` em `engine/base_graph.py` para usar `complete_chat`.
- [x] Integrar `PromptBuilder.build()` em `engine/bootstrap.py` para popular `system_prompt`.
- [x] Integrar `AIProviderResolver` no bootstrap para popular `ai_provider` e `ai_api_key`.
- [x] Mapear `AIProviderNotConfigured` e `LLMProviderError` para `HTTP 502` no endpoint de chat.
- [x] Adicionar testes unitarios do LLM node com mock de provider.
- [x] Atualizar documentacao da task para remover dependencia antiga de `.env` como fonte principal.

## Acceptance Criteria

- [x] `llm_node` chama provider real e popula `final_response` para resposta de texto.
- [x] `llm_node` popula `pending_tool_calls` para tool calls do provider.
- [x] `system_prompt` do `AgentState` vem do `PromptBuilder` no bootstrap.
- [x] Credenciais AI sao resolvidas por tenant/system settings, com `.env` apenas como fallback dev.
- [x] Falhas de provider ou provider ausente retornam `HTTP 502` no endpoint de chat.
- [x] Testes nao fazem chamada real ao provider.

## Verification

```bash
cd backend
.\.venv\Scripts\python -m pytest tests/test_stage_05_llm_node.py tests/test_stage_04_graph.py tests/test_stage_04_engine.py -q
backend\.venv\Scripts\python scripts\validate_openapi.py
python scripts\validate_tasks.py
```

## Risks & Rollback

- **Risks**: provider indisponivel, chave por tenant mal configurada ou retorno de tool call fora do contrato.
- **Rollback**: restaurar `llm_node` placeholder e manter `AIProviderResolver` ativo para nao quebrar configuracoes ja migradas.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para substituir executor placeholder por LLM real.
- `[2026-05-07 00:00]`: Objetivo de `OPENAI_API_KEY` como fonte principal removido; provider passa a ser resolvido por tenant/system settings com fallback dev.
- `[2026-05-07 00:00]`: `engine/llm_client.py` criado e `llm_node` integrado ao provider OpenAI async.
- `[2026-05-07 00:00]`: Endpoint de chat passou a documentar e mapear falhas de provider como `HTTP 502`.
