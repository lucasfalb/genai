# Stage 08 — Channels, Webhooks e Outbound Data Bridge

_Fonte canônica: [`../platform_technical_spec.md`](../platform_technical_spec.md). Este stage reorganiza o conteúdo técnico sem substituir a especificação completa._

## Objetivo

Definir canais de consumo, SessionManager/ResponseManager, API keys, Webhooks, WhatsApp, concorrência por sessão quando acionada via canais e sincronização outbound assíncrona.

## Tabela Relevante

```sql
-- Canais de consumo por instância
CREATE TABLE agent_channel_configs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  instance_id     UUID NOT NULL REFERENCES agent_instances(id),
  channel         TEXT NOT NULL,        -- api | widget | webhook | whatsapp
  config          JSONB NOT NULL DEFAULT '{}',
  outbound_sync_config JSONB NOT NULL DEFAULT '{}',
  is_active       BOOLEAN NOT NULL DEFAULT false,
  api_key         TEXT,                 -- hash; exibida apenas na criação
  allowed_origins TEXT[],               -- para widget: domínios permitidos
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(tenant_id, instance_id, channel)
);
```

## 8. Agent Wrapper — API e Widget

### Canais disponíveis

Cada instância pode ser consumida via API, Widget, Webhook ou WhatsApp. O Tenant Admin ativa e configura cada canal no dashboard e recebe a API key ou credencial específica.

Cada canal também pode receber `outbound_sync_config` em Advanced Settings. Essa configuração define se dados extraídos da conversa serão enviados para uma API ou base externa após a resposta da IA, sem bloquear o streaming para o usuário.

**Canal API:**
```
POST /api/v1/chat
Headers:
  X-Agent-Key: ak_live_...
Body: { "message": "...", "session_id": "..." }
Response: SSE stream de eventos
```

### SessionManager e ResponseManager

O `SessionManager` normaliza entradas vindas de API, Widget, Webhook e WhatsApp para o mesmo contrato interno: `tenant_id`, `instance_id`, `session_id`, `channel`, `sender_id`, `metadata` e mensagem do usuário. Isso mantém o LangGraph independente do canal de origem.

O `ResponseManager` centraliza a etapa final do run: persiste a resposta, envia eventos SSE quando aplicável, registra métricas e aciona integrações assíncronas como o Outbound Data Bridge.

### Concorrência por sessão

Cada `session_id` deve ter no máximo uma execução ativa por vez. Antes de carregar ou gravar estado no checkpointer do LangGraph, o backend adquire um lock distribuído no Redis:

- Chave: `session:{tenant_id}:{session_id}:lock`.
- Aquisição atômica: `SET key run_id NX EX 45`.
- Renovação durante streaming longo.
- Liberação segura apenas se o valor ainda for o mesmo `run_id`.
- Se o lock já existir, a API retorna `409 Conflict` ou enfileira a mensagem em `session:{tenant_id}:{session_id}:queue`, conforme configuração do canal.

O checkpointer mantém `thread_id = session_id`, mas as escritas são serializadas pelo lock. Além disso, cada mensagem persistida recebe `sequence_no` incremental por sessão, garantindo ordenação estável mesmo quando duas requisições chegam quase ao mesmo tempo.

```python
# engine/session_lock.py

class SessionLock:
    async def acquire(self, tenant_id: str, session_id: str, run_id: str) -> bool:
        key = f"session:{tenant_id}:{session_id}:lock"
        return bool(await self.redis.set(key, run_id, nx=True, ex=45))

    async def release(self, tenant_id: str, session_id: str, run_id: str) -> None:
        key = f"session:{tenant_id}:{session_id}:lock"
        await self.redis.eval(
            """
            if redis.call("GET", KEYS[1]) == ARGV[1] then
                return redis.call("DEL", KEYS[1])
            end
            return 0
            """,
            1,
            key,
            run_id,
        )
```

**Canal Widget:**

Script embeddável em qualquer site. Valida o domínio de origem contra `allowed_origins`.
```html


```

**Canal Webhook:**

Recebe mensagens de sistemas externos (WhatsApp, Slack, etc.) e processa assincronamente.
```
POST /api/v1/webhook
Headers: X-Agent-Key: ak_live_...
Body: { "from": "...", "message": "...", "platform": "whatsapp" }
```

**Canal WhatsApp:**

Canal configurável para provedores como Meta Cloud API ou gateways terceiros. Internamente usa o mesmo `SessionManager` e pode compartilhar a infraestrutura de webhook.
```
POST /api/v1/whatsapp/webhook
Headers: X-Provider-Signature: ...
Body: { "from": "+351...", "message": "...", "profile": { "name": "..." } }
```

### Geração automática de API key

Ao ativar um canal, a plataforma gera e exibe a key uma única vez. Internamente é armazenado apenas o hash.

```python
# api/v1/tenant/channels.py

@router.post("/instances/{instance_id}/channels/{channel}/activate")
async def activate_channel(instance_id: UUID, channel: str, tenant: TenantContext = ...):
    raw_key = f"ak_live_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    await db.upsert_channel_config(
        tenant_id=tenant.tenant_id,
        instance_id=instance_id,
        channel=channel,
        outbound_sync_config={
            "enabled": False,
            "destination": {
                "method": "POST",
                "url": None,
                "timeout_seconds": 10,
            },
            "auth_headers_secret_ref": None,
            "field_mapping": {},
            "retry": {"max_attempts": 5, "backoff": "exponential"},
        },
        api_key=key_hash,
        is_active=True,
    )

    # Retorna a key em claro apenas neste momento
    return {"api_key": raw_key, "warning": "Guarde esta key. Ela não será exibida novamente."}
```

### Advanced Settings — outbound_sync_config

```json
{
  "enabled": true,
  "destination": {
    "method": "POST",
    "url": "https://api.cliente.com/leads",
    "timeout_seconds": 10
  },
  "auth_headers_secret_ref": "vault://tenant/acme/outbound/crm_headers",
  "field_mapping": {
    "external_id": "{{ session_id }}",
    "channel": "{{ channel }}",
    "sender": "{{ sender_id }}",
    "name": "{{ metadata.name }}",
    "email": "{{ extracted_entities.email }}",
    "summary": "{{ conversation_summary }}",
    "last_message": "{{ last_user_message }}"
  },
  "retry": {
    "max_attempts": 5,
    "backoff": "exponential"
  }
}
```

O mapping dinâmico permite transformar campos internos em chaves do JSON final. O mapper só publica os campos configurados em `field_mapping`, evitando envio acidental do transcript completo, tool outputs ou dados internos do `AgentState`.

---

## 9. Outbound Data Bridge (External Sync)

### Objetivo

O Outbound Data Bridge permite que canais como API, WhatsApp e Webhooks enviem automaticamente dados extraídos da conversa para uma base de dados ou API externa escolhida pelo tenant. O caso típico é sincronizar leads, tickets, pedidos, entidades extraídas ou resumos de atendimento para um CRM, data warehouse ou backend próprio do cliente.

Essa ponte é assíncrona: a resposta da IA ao usuário não espera o endpoint externo responder.

### Arquitetura lean

```
LangGraph finaliza resposta / entidades
   ↓
ResponseManager persiste resposta e monta payload mapeado
   ↓
OutboundPublisher publica evento mínimo no Redis
   ↓
Worker RQ/Celery consome em background
   ↓
HTTP POST/PUT para API externa do tenant
   ↓
Sucesso, retry com exponential backoff ou dead-letter
```

Componentes:

- **Broker**: Redis existente da stack, reutilizado para fila leve além de lock distribuído e cache.
- **Fila**: RQ ou Celery para Python. RQ é suficiente para a primeira versão; Celery pode ser adotado se houver necessidade de roteamento, prioridades e inspeção operacional mais avançada.
- **Worker**: processo separado do FastAPI, responsável por chamadas externas, retries e dead-letter.
- **Publisher**: roda no caminho quente apenas para mapear dados e enfileirar evento pequeno.

### Integração com SessionManager e ResponseManager

O `SessionManager` continua responsável por resolver `tenant_id`, `session_id`, `channel`, `sender_id` e metadata normalizada de entrada. O `ResponseManager` é o ponto de integração do outbound sync: após persistir a resposta final ou receber `extracted_entities` do grafo LangGraph, ele consulta a configuração do canal e publica o evento assíncrono.

```python
# engine/response_manager.py

class ResponseManager:
    async def finalize(self, state: AgentState, response: AgentResponse) -> None:
        await self.messages.persist_assistant_response(state, response)

        channel_config = await self.channels.get_config(
            tenant_id=state["tenant_id"],
            instance_id=state["instance_id"],
            channel=state["channel"],
        )

        config = channel_config.outbound_sync_config
        if not config.get("enabled"):
            return

        payload = OutboundMapper().render(
            mapping=config["field_mapping"],
            source={
                "tenant_id": state["tenant_id"],
                "instance_id": state["instance_id"],
                "session_id": state["session_id"],
                "channel": state["channel"],
                "sender_id": state.get("sender_id"),
                "metadata": state.get("metadata", {}),
                "extracted_entities": response.extracted_entities,
                "conversation_summary": response.conversation_summary,
                "last_user_message": response.last_user_message,
            },
        )

        await OutboundPublisher(self.redis).enqueue(
            tenant_id=state["tenant_id"],
            channel_config_id=str(channel_config.id),
            method=config["destination"]["method"],
            url=config["destination"]["url"],
            auth_headers_secret_ref=config.get("auth_headers_secret_ref"),
            payload=payload,
            retry=config.get("retry", {}),
        )
```

### Fluxo de execução

1. O LangGraph gera a resposta final e, quando aplicável, `extracted_entities`.
2. O `ResponseManager` persiste a resposta normalmente.
3. O mapper aplica `field_mapping` usando templates como `{{ metadata.name }}` ou `{{ extracted_entities.email }}`.
4. O publisher envia para o Redis apenas o payload mapeado, destino e referência segura de credenciais.
5. O worker consome a fila e executa `POST` ou `PUT`.
6. Em falha temporária, o job é reagendado com exponential backoff.
7. Após esgotar retries, o job vai para dead-letter e aparece no dashboard do canal.

```python
# outbound/worker.py

async def process_outbound_sync(job: OutboundSyncJob) -> None:
    headers = await CredentialCache().get_decrypted_headers(
        tenant_id=job.tenant_id,
        secret_ref=job.auth_headers_secret_ref,
    )

    response = await http_client.request(
        method=job.method,
        url=job.url,
        json=job.payload,
        headers=headers,
        timeout=job.timeout_seconds,
    )
    response.raise_for_status()
```

### Resiliência e Segurança

O Outbound Data Bridge nunca envia o `AgentState` inteiro. O evento da fila contém apenas os campos resultantes do mapping configurado. Isso reduz vazamento acidental de prompts, tool outputs, credenciais ou histórico completo.

Regras obrigatórias:

- Auth Headers e tokens de APIs externas são armazenados como `secret_ref` e tratados com o mesmo nível de criptografia das API keys da instância.
- Secrets nunca entram em logs, traces, payloads da fila ou respostas de API.
- Retentativas usam exponential backoff com jitter para evitar tempestade de chamadas no endpoint do cliente.
- Timeouts curtos por request, default 10s.
- Dead-letter queue para falhas permanentes, com replay manual no dashboard.
- Allowlist opcional de domínios por tenant em planos enterprise.
- Redaction de campos sensíveis nos logs do worker.

### Observabilidade do bridge

```
outbound_sync_jobs_total{tenant_id, instance_id, channel, status}
outbound_sync_duration_seconds{tenant_id, instance_id, channel}
outbound_sync_retries_total{tenant_id, instance_id, channel}
outbound_sync_deadletter_total{tenant_id, instance_id, channel}
```

---
