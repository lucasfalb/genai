# Task: TASK-023 - Base Graph LangGraph

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-023 |
| **Group** | ENGINE |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_04_engine.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

O grafo base organiza RAG, LLM, dispatch de tools e handoff em um fluxo controlado.

## Objectives

- [x] Adicionar dependencia LangGraph quando aprovada.
- [x] Criar `create_base_graph`.
- [x] Criar roteamento `route_after_llm`.
- [x] Criar stubs de nodes testaveis.

## Non-Goals

- Implementar RAG real.
- Implementar LLM provider real.

## Stage Boundaries

Esta task cobre o grafo de execucao do Stage 04 sem executar stages 05, 06 ou 07.

## Dependencies

- TASK-019

## Inputs & Contracts

- **Inputs**: `AgentState`.
- **Outputs**: grafo compilado ou adaptador equivalente.
- **Schemas**: contrato de estado e nomes de nodes.

## Constraints & Rules

1. Dependencia LangGraph deve ser versionada no `pyproject.toml`.
2. Nodes devem ser testaveis sem chamadas externas.
3. Handoff deve rotear por `transfer_tool_name`.

## Implementation Checklist

- [x] Avaliar dependencia LangGraph.
- [x] Implementar base graph.
- [x] Testar roteamento por tool call.
- [x] Documentar limites de stubs.

## Acceptance Criteria

- [x] Grafo compila.
- [x] `route_after_llm` retorna `respond`, `tool_call` ou `handoff`.
- [x] Testes cobrem rotas condicionais.
- [x] Nao ha chamada externa nos testes.

## Verification

```bash
pytest tests/test_stage_04_graph.py
```

## Risks & Rollback

- **Risks**: adicionar LangGraph sem necessidade pode aumentar acoplamento prematuro.
- **Rollback**: manter executor basico e adiar grafo ate Prompt/RAG estarem prontos.

## Execution Log

- `[2026-05-07 14:20]`: Task criada a partir do Stage 04.
- `[2026-05-07 15:10]`: LangGraph adicionado, base graph implementado com nodes stub e testes de roteamento.
