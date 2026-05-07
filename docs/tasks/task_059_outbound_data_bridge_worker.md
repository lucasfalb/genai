# Task: TASK-059 - Outbound Data Bridge Worker e Publisher

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-059 |
| **Group** | CHANNELS |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_08_channels.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

O Outbound Data Bridge envia dados extraidos da conversa para APIs externas do tenant de forma assincrona. O `OutboundPublisher` enfileira um payload mapeado no Redis; o worker consome e executa o POST/PUT com retries e exponential backoff.

## Objectives

- [ ] Implementar `OutboundPublisher` em `outbound/publisher.py` que enfileira job mapeado no Redis.
- [ ] Implementar `OutboundMapper` em `outbound/mapper.py` que aplica `field_mapping` com templates `{{ field }}`.
- [ ] Implementar worker em `outbound/worker.py` que consome fila com BLPOP.
- [ ] Retries com exponential backoff ate `max_attempts`; dead-letter em `outbound:deadletter`.
- [ ] Integrar chamada ao `OutboundPublisher` no `ResponseManager.finalize`.
- [ ] Secrets de auth headers via `CredentialCache` (nunca em claro no payload da fila).
- [ ] Testar: publisher enfileira, mapper aplica templates, worker executa HTTP e trata falha.

## Non-Goals

- UI de dead-letter e replay manual (observabilidade futura).
- Suporte a mais de POST/PUT.

## Stage Boundaries

Publisher e worker de background. Nenhum endpoint admin nesta task.

## Dependencies

- TASK-056 (ResponseManager — ponto de integracao do publisher)

## Inputs & Contracts

- **Inputs**: `field_mapping`, `extracted_entities`, `session_id`, `channel`, `sender_id`, `metadata`.
- **Outputs**: HTTP POST/PUT para API externa; job em dead-letter em falha permanente.
- **Schemas**: `OutboundSyncJob(tenant_id, channel_config_id, method, url, auth_headers_secret_ref, payload, retry)`.

## Constraints & Rules

1. Payload da fila contem apenas campos mapeados — nunca `AgentState` completo.
2. Auth headers descriptografados apenas no worker, nunca no publisher.
3. Timeout por request: 10s (configuravel).
4. Dead-letter apos `max_attempts` esgotados.
5. Secrets nunca em logs ou traces.

## Implementation Checklist

- [ ] Criar `outbound/mapper.py` com template rendering `{{ field }}`.
- [ ] Criar `outbound/publisher.py` com `OutboundPublisher.enqueue`.
- [ ] Criar `outbound/worker.py` com loop BLPOP e retry logic.
- [ ] Integrar `OutboundPublisher` em `ResponseManager.finalize`.
- [ ] Testar: mapper, publisher enfileira, worker executa com mock HTTP, retry apos falha, dead-letter.

## Acceptance Criteria

- [ ] `OutboundMapper` aplica `{{ metadata.name }}` corretamente.
- [ ] Publisher enfileira job sem expor secrets.
- [ ] Worker executa POST e retira job da fila em sucesso.
- [ ] Apos `max_attempts` job vai para dead-letter.

## Verification

```bash
cd backend
pytest tests/test_stage_08_outbound_bridge.py
```

## Risks & Rollback

- **Risks**: endpoint externo lento pode acumular retries e saturar Redis.
- **Rollback**: desabilitar `outbound_sync_config.enabled` no canal; publisher nao enfileira.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para Outbound Data Bridge worker e publisher.
