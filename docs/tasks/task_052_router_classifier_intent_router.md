# Task: TASK-052 - Router Classifier IntentRouter

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-052 |
| **Group** | HANDOFF |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_07_handoff.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Para links com `transfer_mode = router_classifier`, um modelo leve classifica a intencao antes de o agente de origem ser invocado, direcionando diretamente ao agente correto e reduzindo latencia em fluxos previsíveis.

## Objectives

- [ ] Implementar `IntentRouter` em `engine/router.py`.
- [ ] `route(message, tenant_id, default_instance_id)` retorna `instance_id` do agente destino.
- [ ] Consultar `agent_links` com `transfer_mode = router_classifier` para o `default_instance_id`.
- [ ] Montar prompt com regras e chamar modelo leve (gpt-4.1-mini) para classificar.
- [ ] Integrar no endpoint de chat: se existem links de router_classifier, chamar antes do bootstrap.
- [ ] Testar: classificacao correta, nenhuma regra retorna default, timeout retorna default.

## Non-Goals

- Router classifier para links com `transfer_mode = llm_decision` (modo padrao).
- UI de gerenciamento de regras do router.

## Stage Boundaries

Apenas o router. Nao altera o grafo LangGraph diretamente.

## Dependencies

- TASK-050 (linked_agents disponíveis — fonte das regras)

## Inputs & Contracts

- **Inputs**: mensagem do usuario, `tenant_id`, `default_instance_id`.
- **Outputs**: `instance_id` de destino (string UUID).
- **Schemas**: prompt de classificacao com regras de `trigger_description`.

## Constraints & Rules

1. Se nenhuma regra de `router_classifier` existir, retornar `default_instance_id`.
2. Timeout de classificacao: 5s; em timeout retornar `default_instance_id`.
3. Modelo de classificacao configuravel via settings (default `gpt-4.1-mini`).
4. Resposta do LLM deve ser apenas o UUID da instancia destino.

## Implementation Checklist

- [ ] Criar `engine/router.py` com `IntentRouter(db, llm_client)`.
- [ ] Implementar `route` e `_build_routing_prompt`.
- [ ] Integrar chamada ao `IntentRouter` no endpoint de chat antes de iniciar executor.
- [ ] Testar: regra bate, nenhuma regra, timeout.

## Acceptance Criteria

- [ ] Router com regra compativel retorna `instance_id` correto.
- [ ] Router sem regras retorna `default_instance_id`.
- [ ] Timeout retorna `default_instance_id` sem crash.

## Verification

```bash
cd backend
pytest tests/test_stage_07_router.py
```

## Risks & Rollback

- **Risks**: custo adicional de LLM por request com `router_classifier`; classificacao errada desvia o usuario.
- **Rollback**: ignorar `router_classifier` e usar sempre `default_instance_id`.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para router classifier proativo.
