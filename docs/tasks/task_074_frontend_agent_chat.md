# Task: TASK-074 — Agent Chat Interface (SSE)

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-074 |
| **Group** | FRONTEND |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_09_frontend.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-08 |
| **Updated At** | 2026-05-08 |

## Context

O chat com streaming SSE (Server-Sent Events) e o produto principal do GenAI Platform. Esta task implementa a interface de chat completa com streaming de respostas em tempo real, persistencia de sessao e tratamento de erros especificos do engine (provider indisponivel, sessao ja ativa).

## Objectives

- [ ] Criar `frontend/src/lib/api/chat.ts` — cliente SSE para `POST /agent/instances/{id}/chat`.
- [ ] Implementar pagina `/instances/{id}/chat` — interface de chat completa.
- [ ] Consumir eventos SSE: chunks de mensagem e evento de conclusao.
- [ ] Persistir `session_id` para reutilizacao durante a sessao do browser.
- [ ] Tratar erros especificos: 502 (provider indisponivel), 409 (sessao ja ativa/run em progresso).

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

**Formato dos eventos SSE esperados:**
```
data: {"type": "chunk", "content": "parte da resposta"}

data: {"type": "done", "session_id": "uuid-da-sessao"}

data: {"type": "error", "message": "erro no provider"}
```

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

- [ ] Criar `frontend/src/lib/api/chat.ts`:
  - [ ] Funcao `streamChat(instanceId, body, callbacks, signal)`.
  - [ ] Parsear SSE line by line: `data: {json}`.
  - [ ] Chamar `onChunk` para eventos `type: 'chunk'`.
  - [ ] Chamar `onComplete` para eventos `type: 'done'`, extrair `session_id`.
  - [ ] Chamar `onError` para eventos `type: 'error'` e erros HTTP.
  - [ ] Suporte a `AbortSignal` para cancelamento.
- [ ] Criar `frontend/src/routes/(app)/instances/[id]/chat/+page.ts`:
  - [ ] Carregar instancia via `instancesApi.get(id)` para exibir nome no header.
- [ ] Criar `frontend/src/routes/(app)/instances/[id]/chat/+page.svelte`:
  - [ ] Estado: `messages: Message[]`, `currentInput: string`, `isStreaming: boolean`, `sessionId: string | null`.
  - [ ] Interface `Message { role: 'user' | 'agent'; content: string; timestamp: Date }`.
  - [ ] Carregar `sessionId` do `sessionStorage` ao montar.
  - [ ] Funcao `sendMessage()`:
    - [ ] Adicionar mensagem do usuario a `messages`.
    - [ ] Limpar input.
    - [ ] Iniciar placeholder do agente com texto vazio.
    - [ ] Chamar `streamChat()` com callbacks que acumulam chunks.
    - [ ] Ao completar: atualizar `sessionId` em `sessionStorage`.
  - [ ] Scroll automatico para ultima mensagem (via `$effect` ou `afterUpdate`).
  - [ ] Tratamento de erros: exibir bubble de erro inline na conversa.
  - [ ] Botao de cancelar streaming (AbortController).
  - [ ] Input: `<textarea>` com handler de `keydown` (Enter vs Shift+Enter).
- [ ] Criar componente `frontend/src/lib/components/MessageBubble.svelte`:
  - [ ] Props: `role: 'user' | 'agent'`, `content: string`, `isStreaming?: boolean`.
  - [ ] Renderizar markdown basico (negrito, italico, code inline).
  - [ ] Cursor piscante quando `isStreaming === true`.
- [ ] Adicionar link "Chat" na pagina de detalhe da instancia (`/instances/{id}`).

## Acceptance Criteria

- [ ] Mensagem enviada aparece imediatamente na conversa como bubble do usuario.
- [ ] Resposta do agente aparece em tempo real chunk a chunk com cursor piscante.
- [ ] Apos primeira mensagem, `session_id` e reutilizado nas mensagens seguintes.
- [ ] Botao Enviar desabilitado durante streaming.
- [ ] Erro 409 exibe mensagem clara sem quebrar a interface.
- [ ] Erro 502 exibe mensagem sobre provider indisponivel.
- [ ] Navegar para fora cancela o stream sem erros no console.
- [ ] Reload da pagina inicia nova sessao (sem session_id em sessionStorage ainda).

## Verification

```bash
cd frontend
npm run check
# Teste manual: enviar mensagem, verificar streaming, testar 409, navegar para fora durante stream
```

## Risks & Rollback

- **Risco**: SSE via `fetch` tem comportamento diferente em navegadores mais antigos. Mitigacao: verificar suporte a `ReadableStream` e exibir aviso se nao suportado.
- **Risco**: Chunks SSE podem chegar fragmentados pelo TCP — o loop de leitura deve acumular buffer e parsear apenas linhas completas `data: ...`.
- **Risco**: `sessionStorage` e limpo ao fechar a aba — usuario perde o session_id. Isso e aceitavel para MVP; historico persistido e feature futura.
- **Rollback**: Remover arquivos criados — sem alteracoes no backend.

## Execution Log

- `[2026-05-08 00:00]`: Task criada.
