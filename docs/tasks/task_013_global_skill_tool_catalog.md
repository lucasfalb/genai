# Task: TASK-013 - Catalogo Global de Skills e Tools

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-013 |
| **Group** | REGISTRY |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_03_registry.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

O Stage 03 precisa de um catalogo global de skills e tools para que o runtime descubra capacidades disponiveis sem acoplar tudo ao prompt engine.

## Objectives

- [x] Criar repositorio para `skill_definitions`.
- [x] Criar repositorio para `tool_definitions`.
- [x] Criar schemas Pydantic de entrada e saida.
- [x] Criar endpoints superadmin para listar e gerenciar catalogo global.

## Non-Goals

- Executar skills/tools.
- Implementar prompt runtime.

## Stage Boundaries

Esta task se limita ao catalogo global do Stage 03 e nao ativa capacidades por instancia.

## Dependencies

- TASK-010

## Inputs & Contracts

- **Inputs**: payloads superadmin de skill/tool definition.
- **Outputs**: registros globais consultaveis por slug.
- **Schemas**: `skill_definitions`, `tool_definitions` e modelos Pydantic de registry.

## Constraints & Rules

1. Slugs devem ser unicos e estaveis.
2. Schemas JSON devem ser persistidos como JSONB.
3. Endpoints globais devem exigir superadmin.

## Implementation Checklist

- [x] Criar dataclasses e repositorios de catalogo.
- [x] Criar schemas de request/response.
- [x] Criar rotas superadmin.
- [x] Adicionar testes de CRUD minimo.

## Acceptance Criteria

- [x] Superadmin lista skills/tools globais.
- [x] Superadmin cria ou atualiza definition por slug.
- [x] Usuario comum nao acessa endpoints globais.
- [x] Slug duplicado faz upsert controlado.

## Verification

```bash
pytest
backend\.venv\Scripts\python scripts\validate_openapi.py
```

## Risks & Rollback

- **Risks**: catalogo inconsistente pode quebrar descoberta futura do runtime.
- **Rollback**: desativar definitions via `is_active = false` ou remover registros em ambiente nao produtivo.

## Execution Log

- `[2026-05-07 13:00]`: Task criada a partir do Stage 03.
- `[2026-05-07 13:20]`: Repositorio e endpoints superadmin de catalogo implementados.
