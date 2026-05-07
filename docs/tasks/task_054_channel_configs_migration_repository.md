# Task: TASK-054 - agent_channel_configs Migration e Repositorio

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-054 |
| **Group** | CHANNELS |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_08_channels.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Cada canal de consumo (API, Widget, Webhook, WhatsApp) e configurado por instancia com sua propria API key e `outbound_sync_config`. Esta task cria a migration e o repositorio.

## Objectives

- [ ] Criar migration Alembic para tabela `agent_channel_configs` com UNIQUE(tenant_id, instance_id, channel).
- [ ] Implementar `ChannelConfigRepository` em `database/repositories/channel_configs.py`.
- [ ] Operacoes: upsert (activate), get_by_key_hash, get_by_channel, list_by_instance, deactivate.
- [ ] Testar: upsert create e update, get_by_key_hash, unicidade de channel por instancia.

## Non-Goals

- Endpoints de ativacao (TASK-055).
- SessionManager (TASK-056).

## Stage Boundaries

Apenas banco. Nenhum endpoint ou canal nesta task.

## Dependencies

- TASK-003 (tenant-scoped schema — padrao RLS)

## Inputs & Contracts

- **Inputs**: `tenant_id`, `instance_id`, `channel`, `config`, `outbound_sync_config`, `api_key` (hash), `allowed_origins`, `is_active`.
- **Outputs**: `ChannelConfigRecord`.
- **Schemas**: ver DDL em `docs/stages/stage_08_channels.md`.

## Constraints & Rules

1. UNIQUE constraint em `(tenant_id, instance_id, channel)`.
2. `api_key` armazenado apenas como hash SHA-256 — nunca em claro.
3. `channel` aceita: `api | widget | webhook | whatsapp`.
4. `outbound_sync_config` default: `{enabled: false, destination: {method: POST, url: null, timeout_seconds: 10}, retry: {max_attempts: 5, backoff: exponential}}`.

## Implementation Checklist

- [ ] Criar migration `alembic/versions/XXXX_add_agent_channel_configs.py`.
- [ ] Criar `database/repositories/channel_configs.py` com `ChannelConfigRecord` e `ChannelConfigRepository`.
- [ ] Testar: upsert, get_by_key_hash, list_by_instance.

## Acceptance Criteria

- [ ] Migration cria `agent_channel_configs` com constraints corretas.
- [ ] `get_by_key_hash` retorna record correto ou None.
- [ ] Segundo upsert com mesmo channel atualiza registro existente.

## Verification

```bash
cd backend
alembic upgrade head
pytest tests/test_stage_08_repositories.py
```

## Risks & Rollback

- **Rollback**: `alembic downgrade -1`.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para migration e repositorio de agent_channel_configs.
