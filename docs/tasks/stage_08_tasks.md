# Stage 08 Tasks - Channels, Webhooks e Outbound Data Bridge

| ID | Task | Status | Priority | Depends On |
| :--- | :--- | :--- | :--- | :--- |
| TASK-054 | [agent_channel_configs Migration e Repositorio](task_054_channel_configs_migration_repository.md) | PENDING | CRITICAL | TASK-003 |
| TASK-055 | [Channel Activation e API Key Generation](task_055_channel_activation_api_key.md) | PENDING | CRITICAL | TASK-054, TASK-030 |
| TASK-056 | [SessionManager e ResponseManager](task_056_session_manager_response_manager.md) | PENDING | CRITICAL | TASK-021, TASK-054 |
| TASK-057 | [Canal API com SSE e Canal Widget](task_057_api_channel_sse_widget.md) | PENDING | HIGH | TASK-056 |
| TASK-058 | [Canal Webhook e WhatsApp](task_058_webhook_whatsapp_channel.md) | PENDING | HIGH | TASK-056 |
| TASK-059 | [Outbound Data Bridge Worker e Publisher](task_059_outbound_data_bridge_worker.md) | PENDING | HIGH | TASK-056 |
| TASK-060 | [Verificacao Stage 08 Channels](task_060_stage_08_channels_verification.md) | PENDING | HIGH | TASK-055, TASK-057, TASK-058, TASK-059 |

## Scope

Estas tasks cobrem o Stage 08 definido em `docs/stages/stage_08_channels.md`: tabela `agent_channel_configs`, ativacao de canais com API key, SessionManager, ResponseManager, canais API/Widget/Webhook/WhatsApp e Outbound Data Bridge assincrono.

## Implementation Order

1. Migration e repositorio de `agent_channel_configs`.
2. Ativacao de canais e geracao de API key.
3. SessionManager e ResponseManager como base comum de todos os canais.
4. Canal API (SSE) e Canal Widget.
5. Canal Webhook e WhatsApp.
6. Outbound Data Bridge (publisher + worker + retries).
7. Verificacao end-to-end.

## Notes

- API key armazenada apenas como hash SHA-256; exibida em claro somente na ativacao.
- Lock distribuido Redis por `session_id` obrigatorio em todos os canais.
- Outbound sync e assincrono — nao bloqueia resposta ao usuario.
- Toda rota nova deve ganhar request Bruno em `genai-endpoints/`.
- Toda rota JSON usa envelope `ApiResponse[T]`.
