# Task: TASK-056 - SessionManager e ResponseManager

| Atributo       | Valor                              |
| :------------- | :--------------------------------- |
| **ID**         | TASK-056                           |
| **Group**      | CHANNELS                           |
| **Status**     | PENDING                            |
| **Stage Ref**  | `docs/stages/stage_08_channels.md` |
| **Spec Ref**   | `docs/platform_technical_spec.md`  |
| **Priority**   | CRITICAL                           |
| **Owner**      | Unassigned                         |
| **Created At** | 2026-05-07                         |
| **Updated At** | 2026-05-07                         |

## Context

Todos os canais (API, Widget, Webhook, WhatsApp) precisam normalizar entradas para o mesmo contrato interno e centralizar a finalizacao do run. O `SessionManager` normaliza entradas; o `ResponseManager` persiste respostas e aciona outbound sync.

## Objectives

- [ ] Implementar `SessionManager` em `engine/session_manager.py` com `normalize(channel, raw_payload) -> InternalRequest`.
- [ ] Definir `InternalRequest(tenant_id, instance_id, session_id, channel, sender_id, metadata, message)`.
- [ ] Implementar `ResponseManager` em `engine/response_manager.py` com `finalize(state, response)`.
- [ ] `finalize` persiste resposta, aciona outbound publisher se `enabled`.
- [ ] Implementar `verify_agent_api_key(api_key_header) -> AgentContext` em `dependencies/auth.py`.
- [ ] Testar: normalizacao de payload de cada canal, finalize persiste e enfileira.

## Non-Goals

- Canais individuais (TASK-057, TASK-058).
- Worker de outbound (TASK-059).

## Stage Boundaries

Apenas SessionManager e ResponseManager como base. Nenhum endpoint de canal exposto aqui.

## Dependencies

- TASK-021 (persistencia de mensagens — ResponseManager herda logica)
- TASK-054 (ChannelConfigRepository — ResponseManager consulta config de outbound)

## Inputs & Contracts

- **Inputs**: payload bruto de cada canal.
- **Outputs**: `InternalRequest` normalizado; resposta persistida; job enfileirado no Redis.
- **Schemas**: `InternalRequest`, `AgentResponse(text, extracted_entities, conversation_summary, last_user_message)`.

## Constraints & Rules

1. `SessionLock` adquirido antes de qualquer escrita no checkpointer.
2. `verify_agent_api_key` compara hash SHA-256 da key recebida contra banco.
3. `sender_id` para canal API e o `user_id` do token; para WhatsApp e o numero de telefone.
4. `ResponseManager.finalize` nao bloqueia streaming — outbound e assincrono.

## Implementation Checklist

- [ ] Criar `engine/session_manager.py` com `SessionManager` e `InternalRequest`.
- [ ] Criar `engine/response_manager.py` com `ResponseManager` e `AgentResponse`.
- [ ] Adicionar `verify_agent_api_key` em `dependencies/auth.py`.
- [ ] Testar normalizacao de cada canal, verify_api_key valido e invalido.

## Acceptance Criteria

- [ ] `SessionManager.normalize` retorna `InternalRequest` para cada canal.
- [ ] `verify_agent_api_key` retorna 401 para key invalida.
- [ ] `ResponseManager.finalize` persiste resposta e enfileira job quando `enabled`.

## Verification

```bash
cd backend
pytest tests/test_stage_08_session_response_manager.py
```

## Risks & Rollback

- **Risks**: normalizacao incorreta de canal pode misturar `session_id` e criar historico inconsistente.
- **Rollback**: desabilitar canais externos e manter apenas o canal API com Bearer token.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para SessionManager e ResponseManager.
