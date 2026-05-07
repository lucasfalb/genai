# Task: TASK-015 - Metadata Registry Cache

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-015 |
| **Group** | REGISTRY |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_03_registry.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

O prompt runtime precisa recuperar metadata de tools e skills com baixa latencia e invalidacao previsivel.

## Objectives

- [x] Criar servico `ToolMetadataCache`.
- [x] Carregar metadata ativa por tenant e instancia.
- [x] Persistir cache Redis com TTL de 600 segundos.
- [x] Invalidar cache apos ativacao/desativacao.

## Non-Goals

- Montar prompt final.
- Executar chamadas a LLM.

## Stage Boundaries

Esta task cobre apenas resolucao e cache de metadata do Stage 03.

## Dependencies

- TASK-014

## Inputs & Contracts

- **Inputs**: tenant id e instance id.
- **Outputs**: metadata serializada de skills e tools ativas.
- **Schemas**: modelos Pydantic de metadata.

## Constraints & Rules

1. Cache deve ter chave namespaced por tenant e instancia.
2. Fallback para PostgreSQL deve funcionar se Redis falhar.
3. Metadata nao deve conter segredos.

## Implementation Checklist

- [x] Criar modelos de metadata.
- [x] Criar servico de cache.
- [x] Integrar invalidacao nas mutacoes de ativacao.
- [x] Testar cache hit/miss e payload sem segredos.

## Acceptance Criteria

- [x] Metadata de instancia retorna skills/tools ativos.
- [x] Cache Redis e usado quando disponivel.
- [x] Invalidacao remove chave correta.
- [x] Payload nao inclui credenciais.

## Verification

```bash
pytest
```

## Risks & Rollback

- **Risks**: cache desatualizado pode expor capacidade desativada no runtime.
- **Rollback**: reduzir TTL para zero temporariamente ou invalidar chaves de metadata.

## Execution Log

- `[2026-05-07 13:00]`: Task criada a partir do Stage 03.
- `[2026-05-07 13:20]`: Metadata cache implementado com fallback quando Redis falha.
- `[2026-05-07 13:35]`: Status ajustado para IN_PROGRESS; falta teste especifico de hit/miss e invalidacao de cache.
- `[2026-05-07 14:05]`: Teste com Redis falso validou cache hit, miss e invalidacao.
