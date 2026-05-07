# Task: TASK-021 - Executor Basico e Persistencia de Mensagens

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-021 |
| **Group** | ENGINE |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_04_engine.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Antes do LangGraph completo, o backend precisa de um executor que normalize entrada, aplique lock e persista mensagens em ordem.

## Objectives

- [x] Criar executor basico assincorno.
- [x] Criar ou reutilizar sessao.
- [x] Persistir mensagem do usuario e resposta.
- [x] Registrar eventos estruturados do run.

## Non-Goals

- Chamar LLM externo.
- Executar tools reais.

## Stage Boundaries

Esta task entrega o fluxo minimo de execucao do Stage 04 sem implementar prompts ou RAG.

## Dependencies

- TASK-019
- TASK-020

## Inputs & Contracts

- **Inputs**: mensagem, session id opcional, tenant id, instance id e channel.
- **Outputs**: eventos de run e mensagens persistidas.
- **Schemas**: `sessions`, `messages` e eventos Pydantic.

## Constraints & Rules

1. `sequence_no` deve ser monotono por sessao.
2. Lock deve ser liberado mesmo em erro controlado.
3. Resposta deterministica local deve ficar marcada como placeholder.

## Implementation Checklist

- [x] Criar `AgentExecutor`.
- [x] Integrar `SessionRepository`.
- [x] Integrar `SessionLock`.
- [x] Testar liberacao de lock em erro.

## Acceptance Criteria

- [x] Executor persiste mensagem user e assistant.
- [x] Sequencia de mensagens fica ordenada.
- [x] Execucao concorrente retorna conflito.
- [x] Erros nao deixam lock preso.

## Verification

```bash
pytest tests/test_stage_04_engine.py
```

## Risks & Rollback

- **Risks**: persistencia parcial pode duplicar mensagens ou quebrar ordering.
- **Rollback**: desabilitar endpoint de chat e limpar sessoes de teste.

## Execution Log

- `[2026-05-07 14:20]`: Task criada a partir do Stage 04.
- `[2026-05-07 14:35]`: Executor basico implementado com resposta placeholder e persistencia ordenada.
- `[2026-05-07 15:10]`: Executor refatorado para `start_stream`, release em erro e eventos estruturados testados.
