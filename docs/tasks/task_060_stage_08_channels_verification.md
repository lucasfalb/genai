# Task: TASK-060 - Verificacao Stage 08 Channels

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-060 |
| **Group** | CHANNELS |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_08_channels.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Antes de encerrar o roadmap principal, os canais precisam estar validados: migration, ativacao, SessionManager, canais API/Widget/Webhook/WhatsApp e Outbound Data Bridge.

## Objectives

- [ ] Executar suite pytest completa.
- [ ] Executar validador OpenAPI.
- [ ] Executar validador de tasks.
- [ ] Verificar cobertura Bruno para endpoints de channels.
- [ ] Confirmar que API key nunca aparece em logs ou respostas de listagem.
- [ ] Confirmar que outbound payload nao expoe AgentState completo.

## Non-Goals

- Teste de carga de canais.
- Validacao de integracao com provedor WhatsApp real.

## Stage Boundaries

Validacao somente do Stage 08 e regressao dos stages anteriores.

## Dependencies

- TASK-055, TASK-057, TASK-058, TASK-059

## Inputs & Contracts

- **Inputs**: backend, migrations, Bruno collection e scripts de validacao.
- **Outputs**: evidencias de validacao completa.
- **Schemas**: OpenAPI e arquivos `.bru`.

## Constraints & Rules

1. Toda rota nova deve ter request Bruno.
2. API key nunca pode aparecer em logs ou respostas de listagem.
3. Outbound payload nunca deve expor `AgentState` completo.
4. Nenhuma regressao nos testes dos stages anteriores.

## Implementation Checklist

- [ ] Rodar `pytest`.
- [ ] Rodar `validate_openapi.py`.
- [ ] Rodar `validate_tasks.py`.
- [ ] Conferir `genai-endpoints/TenantChannels/` contra rotas novas.
- [ ] Auditar logs de teste para garantir ausencia de secrets.
- [ ] Registrar pendencias residuais.

## Acceptance Criteria

- [ ] Pytest passa sem falhas.
- [ ] OpenAPI valido.
- [ ] Tasks validadas.
- [ ] Bruno cobre channels CRUD e ativacao.
- [ ] Nenhum secret em logs.

## Verification

```bash
docker compose up -d postgres redis qdrant
cd backend
alembic upgrade head
pytest
cd ..
backend\.venv\Scripts\python scripts\validate_openapi.py
python scripts\validate_tasks.py
```

## Risks & Rollback

- **Risks**: falha no lock distribuido pode permitir execucoes concorrentes corrompendo historico.
- **Rollback**: manter Stage 08 aberto e bloquear deploys de producao.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para verificacao final do Stage 08.
