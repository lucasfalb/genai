# Task: TASK-058 - Canal Webhook e WhatsApp

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-058 |
| **Group** | CHANNELS |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_08_channels.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Canais Webhook e WhatsApp recebem mensagens de sistemas externos e processam assincronamente usando o mesmo `SessionManager`. O canal WhatsApp adiciona validacao de assinatura do provedor.

## Objectives

- [ ] Criar `POST /api/v1/webhook` autenticado por `X-Agent-Key` para canal generico.
- [ ] Criar `POST /api/v1/whatsapp/webhook` com validacao de `X-Provider-Signature`.
- [ ] Normalizar entrada via `SessionManager.normalize(channel='webhook'|'whatsapp', ...)`.
- [ ] Processar mensagem de forma assincrona (enfileirar no Redis, responder 202 imediatamente).
- [ ] Adicionar requests Bruno em `genai-endpoints/`.

## Non-Goals

- Integracao com provedor Meta Cloud API real (apenas contrato de assinatura).
- Resposta de retorno por webhook (outbound — TASK-059).

## Stage Boundaries

Apenas recepcao e enfileiramento. O worker de execucao do grafo fica fora do escopo desta task.

## Dependencies

- TASK-056 (SessionManager, verify_agent_api_key)

## Inputs & Contracts

- **Inputs webhook**: `X-Agent-Key`, `{from: str, message: str, platform: str}`.
- **Inputs whatsapp**: `X-Provider-Signature`, `{from: str, message: str, profile: {name: str}}`.
- **Outputs**: HTTP 202 Accepted imediatamente; job enfileirado para processamento.
- **Schemas**: `WebhookRequest`, `WhatsAppRequest`.

## Constraints & Rules

1. `X-Agent-Key` verificado para canal `webhook`.
2. `X-Provider-Signature` verificado com HMAC-SHA256 da secret configurada no canal `whatsapp`.
3. Ambos os canais retornam 202 imediatamente sem aguardar execucao do grafo.
4. `session_id` derivado de `from` (numero ou ID do remetente) para garantir historico consistente.

## Implementation Checklist

- [ ] Criar `api/v1/agent/webhook.py` com endpoint webhook generico.
- [ ] Criar `api/v1/agent/whatsapp.py` com validacao HMAC-SHA256.
- [ ] Enfileirar job `{internal_request}` em Redis `agent:execution_queue:{instance_id}`.
- [ ] Registrar routers em `app/main.py`.
- [ ] Testar: webhook com key valida 202, assinatura invalida whatsapp 401.

## Acceptance Criteria

- [ ] Webhook com key valida retorna 202.
- [ ] WhatsApp com assinatura invalida retorna 401.
- [ ] Job enfileirado no Redis apos recepcao.

## Verification

```bash
cd backend
pytest tests/test_stage_08_webhook_whatsapp.py
```

## Risks & Rollback

- **Risks**: assinatura WhatsApp dependente do provedor — ajustar algoritmo por provedor configurado.
- **Rollback**: desabilitar routers de webhook e whatsapp.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para canal Webhook e WhatsApp.
