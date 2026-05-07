# Task: TASK-005 - Sessoes, Mensagens e Auditoria

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-005 |
| **Group** | CORE |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_01_core_db.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Conversas sao o principal estado operacional do agente. Esta task formaliza a persistencia de `sessions`, `messages` e `audit_logs`, incluindo sequenciamento de mensagens e rastreabilidade minima para fluxos futuros de Engine, Channels e Observability.

## Objectives

- [x] Garantir schema final de `sessions`.
- [x] Garantir schema final de `messages`.
- [x] Garantir `UNIQUE(session_id, sequence_no)`.
- [x] Definir estrategia atomica para gerar `sequence_no` por sessao.
- [x] Garantir atualizacao de `sessions.last_message_at` ao persistir mensagem.
- [x] Definir contrato append-only para `audit_logs`.

## Non-Goals

- Implementar execucao LangGraph.
- Implementar streaming SSE.
- Implementar analytics ou traces completos.

## Stage Boundaries

A task entrega persistencia e contratos de estado conversacional. Concorrencia distribuida por Redis Lock pertence ao Stage 04, mas deve ser considerada como dependencia futura.

## Dependencies

- TASK-002.
- TASK-003.
- TASK-004.

## Inputs & Contracts

- **Inputs**: `tenant_id`, `instance_id`, `channel`, `user_ref`, metadata e conteudo da mensagem.
- **Outputs**: sessao criada/atualizada, mensagem persistida e auditoria append-only quando aplicavel.
- **Schemas**: `sessions`, `messages`, `audit_logs`.

## Constraints & Rules

1. Mensagens devem ser ordenaveis por `sequence_no` dentro da sessao.
2. `sequence_no` nao pode duplicar para a mesma sessao.
3. `messages.tenant_id` deve corresponder ao tenant da sessao.
4. `audit_logs` nao deve armazenar secrets ou payloads sensiveis em claro.
5. Alteracoes devem respeitar RLS quando a tabela for tenant-scoped.

## Implementation Checklist

- [x] Revisar schema de sessoes e mensagens.
- [x] Criar repository/service minimo para persistencia conversacional.
- [x] Implementar criacao ou recuperacao de sessao.
- [x] Implementar append de mensagem com sequenciamento atomico.
- [x] Atualizar `last_message_at`.
- [x] Implementar helper de auditoria append-only.
- [x] Criar testes de ordenacao, duplicidade e isolamento por tenant.

## Acceptance Criteria

- [x] Uma sessao pode receber mensagens ordenadas sem duplicidade de `sequence_no`.
- [x] Tentativa de duplicar `sequence_no` falha no banco.
- [x] `last_message_at` reflete a ultima mensagem persistida.
- [x] Mensagens de outro tenant nao sao visiveis sob RLS.
- [x] Auditoria registra acao, recurso, usuario/tenant quando disponiveis e metadata sanitizada.
- [x] Acoes de superadmin em escopo de tenant preservam `tenant_id`, `user_id`, `actor_type` e `actor_role`.

## Verification

```bash
pytest
```

## Risks & Rollback

- **Risks**: race condition no sequenciamento antes do Redis Lock; auditoria capturar dados sensiveis; inconsistencias entre `messages.tenant_id` e `sessions.tenant_id`.
- **Rollback**: desativar services de escrita conversacional e corrigir constraint/transaction antes de expor canais.

## Execution Log

- `[2026-05-07 00:00]`: Task criada a partir do Stage 01.
- `[2026-05-07 12:20]`: Tabelas `sessions`, `messages` e `audit_logs` criadas.
- `[2026-05-07 12:35]`: Repositories de sessoes/mensagens e auditoria implementados com testes.
- `[2026-05-07 13:05]`: Auditoria recebeu contexto de ator para rastrear acoes de superadmin por tenant.
