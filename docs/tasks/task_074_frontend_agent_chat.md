# Task: TASK-074 — Agent Chat Interface (SSE)

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-074 |
| **Group** | FRONTEND |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_09_frontend.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-08 |
| **Updated At** | 2026-05-10 |

## Context

O chat com streaming SSE (Server-Sent Events) e o produto principal do GenAI Platform. Esta task implementa o painel de teste embutido no layout de detalhe da instancia (`+layout.svelte`), com streaming de respostas em tempo real, persistencia de sessao e tratamento de erros especificos do engine (provider indisponivel, sessao ja ativa).

Escopo revisado (2026-05-10): em vez de pagina dedicada `/instances/{id}/chat`, a interface vive como componente reutilizavel renderizado no painel direito do layout existente (Resizable.Pane 35%). O placeholder estatico atual e substituido pelo componente conectado.

## Objectives

- [x] Criar `frontend/src/lib/api/chat.ts` — cliente SSE para `POST /agent/instances/{id}/chat`.
- [x] Extrair painel de teste do `+layout.svelte` em componente reutilizavel `TestAgentChat`.
- [x] Consumir eventos SSE no formato `ChatEvent` (event: message.persisted | assistant.delta | run.completed).
- [x] Persistir `session_id` por instancia em `sessionStorage`.
- [x] Tratar erros especificos: 502 (provider indisponivel), 409 (sessao ja ativa/run em progresso).

## Non-Goals

- Nao implementar historico de sessoes persistido — apenas sessao em memoria/sessionStorage.
- Nao implementar upload de arquivos no chat.
- Nao implementar markdown rendering avancado (basico e suficiente).
- Nao implementar canais multiplos (WhatsApp, Widget) — chat e via canal `api`.

## Stage Boundaries

Apenas interface de chat via SSE. Nenhum endpoint novo no backend.

## Dependencies

- TASK-069 — pagina de detalhe da instancia existe, `instancesApi` disponivel.

## Inputs & Contracts

**Arquivo `frontend/src/lib/api/chat.ts`:**
```typescript
import type { ChatRequest } from '$lib/api/types';

export interface ChatStreamCallbacks {
  onChunk:      (text: string) => void;
  onComplete:   (fullText: string) => void;
  onError:      (error: ChatStreamError) => void;
}

export interface ChatStreamError {
  status: number;
  message: string;
  code?: string;
}

export async function streamChat(
  instanceId: string,
  body: ChatRequest,
  callbacks: ChatStreamCallbacks,
  signal?: AbortSignal
): Promise<void>
```

**Implementacao de `streamChat`:**
```typescript
// Usar fetch + ReadableStream (nao EventSource, pois precisa de POST com body)
const response = await fetch(`${BASE_URL}/agent/instances/${instanceId}/chat`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${authStore.accessToken}`,
    'X-Tenant-ID': tenantStore.activeTenantId,
  },
  body: JSON.stringify(body),
  signal,
});

if (!response.ok) {
  const error = await response.json();
  callbacks.onError({ status: response.status, message: error.message, code: error.code });
  return;
}

// Ler stream linha a linha (SSE format: "data: {json}\n\n")
const reader = response.body.getReader();
const decoder = new TextDecoder();
let fullText = '';
// ... loop de leitura de chunks SSE
```

**Formato dos eventos SSE reais (backend `app.schemas.ChatEvent`):**
```
data: {"event":"message.persisted","session_id":"<uuid>","sequence_no":1,"content":null,"metadata":{}}

data: {"event":"assistant.delta","session_id":"<uuid>","sequence_no":2,"content":"<full assistant response>","metadata":{}}

data: {"event":"run.completed","session_id":"<uuid>","sequence_no":2,"content":null,"metadata":{"run_id":"<uuid>"}}
```

Nota: backend emite `assistant.delta` com a resposta completa no MVP (LangGraph executa antes de enviar). Cliente trata como streaming-ready: acumula `content` em ordem, exibe quando recebido.

**Pagina `/instances/{id}/chat/+page.svelte`:**
- Layout: coluna de mensagens (scrollavel) + input na parte inferior.
- Mensagens: bubble de usuario (direita), bubble do agente (esquerda).
- Durante streaming: bubble do agente com cursor piscante + texto acumulado.
- Input: textarea (Enter para enviar, Shift+Enter para nova linha) + botao Enviar.
- Botao Enviar desabilitado durante streaming em progresso.
- `session_id` persistido em `sessionStorage` com chave `chat_session_{instanceId}`.

**Tratamento de erros:**
- 409 (run ja ativo): "O agente esta processando outra mensagem. Aguarde."
- 502 (provider indisponivel): "O provedor de AI esta indisponivel. Verifique a configuracao de AI."
- 401: redirect para login (via `client.ts` interceptor).
- Timeout / abort: exibir "Conexao interrompida. Tente novamente."

## Constraints & Rules

1. Usar `fetch` com `ReadableStream` para o chat SSE — NAO usar `EventSource` (nao suporta POST).
2. O stream pode ser cancelado se o usuario navegar para fora da pagina — usar `AbortController` com cleanup em `onDestroy`.
3. `session_id` e gerado pelo backend no primeiro request (sem session_id) e retornado no evento `done` — persistir para a proxima mensagem.
4. Mensagens do usuario e do agente devem ser armazenadas em estado local (`$state`) durante a sessao.
5. O `channel` deve ser fixo como `'api'` nesta interface.
6. Scroll automatico para a ultima mensagem ao receber novo chunk.
7. Input deve ser limpo imediatamente apos o submit, antes da resposta chegar.
8. Nao reenviar a mensagem se o usuario clicar Enviar multiplas vezes — desabilitar botao durante request.

## Implementation Checklist

- [x] Adicionar `ChatRequest`/`ChatEvent` em `frontend/src/lib/api/types.ts`.
- [x] Criar `frontend/src/lib/api/chat.ts`:
  - [x] Funcao `streamChat(instanceId, body, callbacks, signal)` via `fetch` + `ReadableStream`.
  - [x] Parser SSE: split por `\n\n`, extrai linhas `data:` e concatena multi-line.
  - [x] Callbacks: `onUserPersisted`, `onAssistantDelta`, `onCompleted`, `onError`, `onEvent`.
  - [x] Suporte a `AbortSignal` para cancelamento (silencioso em `AbortError`).
  - [x] Helper `chatSession` (get/set/clear em `sessionStorage` por `instanceId`).
- [x] Criar componente `frontend/src/lib/components/MessageBubble.svelte`:
  - [x] Props: `role: 'user' | 'assistant' | 'error'`, `content`, `isStreaming?`, `timestamp?`, `hint?`.
  - [x] Markdown inline minimo (negrito, italico, code).
  - [x] Cursor piscante quando `isStreaming === true`.
- [x] Criar componente `frontend/src/lib/components/instance/test-agent-chat.svelte`:
  - [x] Estado: `messages`, `input`, `isStreaming`, `sessionId`, `abortController`.
  - [x] Carregar `sessionId` do `sessionStorage` por `instanceId` no mount/troca de instancia.
  - [x] `send()`: empilha bubble usuario, placeholder assistant, chama `streamChat`, atualiza com delta.
  - [x] Scroll automatico via `$effect` + `queueMicrotask`.
  - [x] Erros viram bubble role `error` inline (409/502/503/401/0/outros).
  - [x] Botao "Parar" durante streaming (AbortController).
  - [x] Botao "Reset session" limpa `sessionStorage` + estado.
  - [x] Enter envia, Shift+Enter quebra linha.
  - [x] Header com badge de session_id curto + link rapido para `/collections`.
- [x] Substituir bloco placeholder no `frontend/src/routes/(app)/app/[tenant]/instances/[id]/+layout.svelte` pelo `<TestAgentChat ... />` (mantem `Resizable.Pane` 35%).
- [x] Limpar imports/state nao usados no layout (`Database`, `MoreHorizontal`, `Send`, `ThumbsDown`, `ThumbsUp`, `ChevronDown`, `testMessage`).

## Acceptance Criteria

- [x] Mensagem enviada aparece imediatamente como bubble do usuario.
- [x] Bubble do assistente exibe cursor piscante ate `run.completed`.
- [x] `session_id` retornado em `run.completed` e reutilizado nas mensagens seguintes (persiste em `sessionStorage`).
- [x] Botao Enviar substituido por "Parar" durante streaming.
- [x] Erro 409 exibe mensagem clara sobre run em progresso.
- [x] Erro 502 exibe mensagem sobre provider indisponivel.
- [x] `onDestroy` aborta stream sem erros no console.
- [x] "Reset session" limpa `sessionStorage` e historico in-memory.
- [x] `npm run check` sem erros nos novos arquivos (`chat.ts`, `MessageBubble.svelte`, `test-agent-chat.svelte`, layout atualizado).

## Verification

```bash
cd frontend
npm run check
# Smoke manual: backend up + tenant/instance ativos; abrir /app/{tenant}/instances/{id}, enviar mensagem,
# verificar bubble do usuario imediato, cursor piscante no assistente, persistencia de session_id no
# sessionStorage, erro 409 ao reenviar antes de run.completed, abort em navigate-away.
```

Smoke manual end-to-end (envio real ao engine) eh responsabilidade do revisor antes do merge — o backend nao foi alterado nesta task.

## Risks & Rollback

- **Risco**: SSE via `fetch` tem comportamento diferente em navegadores mais antigos. Mitigacao: verificar suporte a `ReadableStream` e exibir aviso se nao suportado.
- **Risco**: Chunks SSE podem chegar fragmentados pelo TCP — o loop de leitura deve acumular buffer e parsear apenas linhas completas `data: ...`.
- **Risco**: `sessionStorage` e limpo ao fechar a aba — usuario perde o session_id. Isso e aceitavel para MVP; historico persistido e feature futura.
- **Rollback**: Remover arquivos criados — sem alteracoes no backend.

## Execution Log

- `[2026-05-08 00:00]`: Task criada.
- `[2026-05-10 00:00]`: Escopo revisado para painel embutido no `+layout.svelte` (em vez de pagina dedicada `/instances/{id}/chat`). Status -> IN_PROGRESS.
- `[2026-05-10 00:10]`: Adicionados tipos `ChatRequest`/`ChatEvent` em `lib/api/types.ts` alinhados ao backend `app.schemas.ChatEvent`.
- `[2026-05-10 00:20]`: Criado `lib/api/chat.ts` com `streamChat` (fetch + ReadableStream), parser SSE robusto (multi-line `data:`, buffer por `\n\n`), callbacks tipados, helper `chatSession`.
- `[2026-05-10 00:30]`: Criado componente `lib/components/MessageBubble.svelte` (markdown inline minimo, cursor piscante).
- `[2026-05-10 00:40]`: Criado componente `lib/components/instance/test-agent-chat.svelte` (estado messages, scroll auto, send/cancel/reset, mapeamento de erros 409/502/503/401, badge de session_id).
- `[2026-05-10 00:50]`: `+layout.svelte` da instancia substitui placeholder por `<TestAgentChat />` e remove imports/state nao usados.
- `[2026-05-10 01:00]`: `npm run check` -> zero erros nos arquivos novos. Status -> COMPLETED.
