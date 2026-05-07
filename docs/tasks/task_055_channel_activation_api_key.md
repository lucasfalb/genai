# Task: TASK-055 - Channel Activation e API Key Generation

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-055 |
| **Group** | CHANNELS |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_08_channels.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Tenant admins ativam canais por instancia e recebem a API key gerada uma unica vez. Esta task expoe os endpoints de ativacao, desativacao e configuracao de canal, gerando e armazenando a API key como hash.

## Objectives

- [ ] Criar `APIRouter` em `api/v1/tenant_channels.py` com prefix `/tenant/instances/{instance_id}/channels`.
- [ ] `POST /tenant/instances/{instance_id}/channels/{channel}/activate` — gera API key, salva hash, retorna key em claro.
- [ ] `POST /tenant/instances/{instance_id}/channels/{channel}/deactivate` — desativa canal.
- [ ] `GET /tenant/instances/{instance_id}/channels` — listar canais e status (sem expor key).
- [ ] `PATCH /tenant/instances/{instance_id}/channels/{channel}` — atualizar `outbound_sync_config` e `allowed_origins`.
- [ ] Adicionar requests Bruno em `genai-endpoints/TenantChannels/`.

## Non-Goals

- Verificacao de dominio de widget (feita em runtime no TASK-057).
- Rotacao de API key (gerar nova revoga a anterior via upsert).

## Stage Boundaries

Apenas gerenciamento de configuracao de canal. Nenhum runtime de canal.

## Dependencies

- TASK-054 (repositorio de channel_configs)
- TASK-030 (RBAC — autenticacao tenant-scoped)

## Inputs & Contracts

- **Inputs**: `channel` (api|widget|webhook|whatsapp), `outbound_sync_config`, `allowed_origins`.
- **Outputs**: `ChannelActivationResponse(channel, is_active, api_key, warning)` apenas na ativacao; `ChannelConfigResponse` nos demais.
- **Schemas**: `ChannelActivationResponse`, `ChannelConfigResponse`, `ChannelUpdateRequest`, `ApiResponse[T]`.

## Constraints & Rules

1. `api_key` = `f"ak_live_{secrets.token_urlsafe(32)}"` gerado na ativacao.
2. Hash SHA-256 armazenado; chave em claro retornada apenas na resposta de ativacao com aviso.
3. Requer Bearer token, `X-Tenant-ID` e permissao `MANAGE_AGENT_INSTANCES`.
4. `outbound_sync_config.destination.url` validado como URL quando `enabled = true`.

## Implementation Checklist

- [ ] Criar schemas em `app/schemas.py`.
- [ ] Criar `api/v1/tenant_channels.py` com 4 endpoints.
- [ ] Registrar router em `app/main.py`.
- [ ] Adicionar Bruno requests.
- [ ] Testar: activate retorna key, deactivate, update config, list channels.

## Acceptance Criteria

- [ ] Activate retorna `api_key` em claro com `warning`.
- [ ] Get channels nao expoe `api_key`.
- [ ] Segundo activate gera nova key (rotacao via upsert).
- [ ] Deactivate muda `is_active = false`.

## Verification

```bash
cd backend
pytest tests/test_stage_08_channels.py
```

## Risks & Rollback

- **Risks**: key em claro exposta em log se response for logado sem redaction.
- **Rollback**: remover router de `app/main.py`.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para ativacao de canais e geracao de API key.
