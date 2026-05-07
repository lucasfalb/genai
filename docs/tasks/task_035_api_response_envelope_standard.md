# Task: TASK-035 - API Response Envelope Standard

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-035 |
| **Group** | SECURITY |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_05_base_multitenant_workflows.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Codex |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Os endpoints retornavam formatos inconsistentes: sucesso devolvia diretamente o recurso e erros usavam o `detail` padrao do FastAPI. Isso dificulta frontend, toasts, acoes por codigo de erro e documentacao Swagger.

## Objectives

- [x] Criar envelope padrao para respostas JSON de sucesso.
- [x] Criar envelope padrao para erros HTTP e erros de validacao.
- [x] Aplicar envelope nos endpoints JSON existentes sem alterar SSE.
- [x] Atualizar validadores/skill para preservar o contrato nos proximos endpoints.

## Non-Goals

- Alterar payload de Server-Sent Events.
- Implementar frontend de toasts.
- Mapear todos os erros para codigos de negocio definitivos.

## Stage Boundaries

Esta task altera contratos de API compartilhados usados pelos workflows base do Stage 05 e preserva os endpoints implementados nos stages anteriores.

## Dependencies

- TASK-026

## Inputs & Contracts

- **Inputs**: responses FastAPI, `HTTPException`, erros de validacao Pydantic.
- **Outputs**: sucesso JSON em `{"status":"success","message":...,"data":...,"meta":{...}}` e erro JSON em `{"status":"error","error":{"code":...,"message":...,"details":...}}`.
- **Schemas**: `ApiResponse[T]`, `ApiError`, `ApiErrorResponse`.

## Constraints & Rules

1. Endpoints JSON devem declarar `response_model=ApiResponse[T]`.
2. Handlers globais devem normalizar `HTTPException` e `RequestValidationError`.
3. Endpoints SSE mantem `text/event-stream` e nao usam envelope de sucesso.
4. Mensagens de erro nao devem expor secrets, tokens, hashes ou credenciais.
5. O validador OpenAPI deve rejeitar responses JSON de sucesso fora do envelope.

## Implementation Checklist

- [x] Adicionar schemas de envelope em `backend/app/schemas.py`.
- [x] Adicionar helper `api_success(...)` e handlers globais de erro.
- [x] Aplicar `ApiResponse[T]` em auth, registry, superadmin e healthcheck.
- [x] Atualizar testes para validar `data` e `error`.
- [x] Atualizar `endpoint-contract-guardian` e `validate_openapi.py`.
- [x] Rodar testes e validadores.

## Acceptance Criteria

- [x] Registro retorna `status=success`, mensagem e usuario dentro de `data`.
- [x] Login bloqueado por conta inativa retorna `status=error` e `error.code`.
- [x] OpenAPI documenta o envelope de sucesso.
- [x] Suite automatizada passa sem regressao conhecida.

## Verification

```bash
cd backend
.\.venv\Scripts\python -m pytest -q
cd ..
backend\.venv\Scripts\python scripts\validate_openapi.py
python scripts\validate_tasks.py
```

## Risks & Rollback

- **Risks**: clients existentes que consumiam o recurso direto precisam ler `data`.
- **Rollback**: remover `ApiResponse[T]` dos endpoints e handlers globais, mantendo testes antigos.

## Execution Log

- `[2026-05-07 17:10]`: Envelope padrao criado e aplicado aos endpoints JSON existentes.
- `[2026-05-07 17:20]`: Skill de endpoint e validador OpenAPI atualizados para exigir `ApiResponse`.
