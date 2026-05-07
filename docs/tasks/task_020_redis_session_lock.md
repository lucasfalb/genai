# Task: TASK-020 - Redis Session Lock

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-020 |
| **Group** | ENGINE |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_04_engine.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Cada sessao deve aceitar no maximo uma execucao ativa para preservar sequencia de mensagens e estado do checkpointer.

## Objectives

- [x] Implementar lock Redis com `SET NX EX`.
- [x] Liberar lock apenas quando o valor ainda for o `run_id`.
- [x] Renovar lock durante streaming longo.
- [x] Retornar conflito quando a sessao estiver bloqueada.

## Non-Goals

- Implementar fila de mensagens por canal.
- Implementar checkpointer LangGraph.

## Stage Boundaries

Esta task cobre apenas serializacao concorrente por sessao.

## Dependencies

- TASK-005

## Inputs & Contracts

- **Inputs**: tenant id, session id e run id.
- **Outputs**: lock adquirido/liberado ou conflito.
- **Schemas**: chave Redis `session:{tenant_id}:{session_id}:lock`.

## Constraints & Rules

1. Lock deve ter TTL para evitar deadlock permanente.
2. Release deve ser compare-and-delete atomico.
3. Falha de Redis nao deve simular sucesso silencioso.

## Implementation Checklist

- [x] Criar `SessionLock`.
- [x] Criar excecao de conflito.
- [x] Testar acquire/release.
- [x] Testar renovacao de TTL.

## Acceptance Criteria

- [x] Primeiro acquire retorna sucesso.
- [x] Segundo acquire para mesma sessao retorna conflito.
- [x] Release com run id incorreto nao remove lock.
- [x] Lock pode ser renovado para streaming longo.

## Verification

```bash
pytest tests/test_stage_04_engine.py
```

## Risks & Rollback

- **Risks**: lock incorreto pode permitir runs concorrentes ou travar sessoes.
- **Rollback**: desabilitar endpoint de chat e remover chaves `session:*:lock` em ambiente local.

## Execution Log

- `[2026-05-07 14:20]`: Task criada a partir do Stage 04.
- `[2026-05-07 14:35]`: Lock Redis implementado com acquire, conflito e release seguro; renovacao segue pendente.
- `[2026-05-07 15:10]`: Renovacao de TTL por compare-and-expire implementada e testada.
