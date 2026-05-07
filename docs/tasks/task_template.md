# Task: TASK-000 — Titulo Curto da Entrega

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-000 |
| **Group** | CORE \| AUTH \| REGISTRY \| ENGINE \| PROMPTS \| RAG \| HANDOFF \| CHANNELS \| OBSERVABILITY \| SECURITY |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_0x_name.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | LOW \| MEDIUM \| HIGH \| CRITICAL |
| **Owner** | Unassigned |
| **Created At** | YYYY-MM-DD |
| **Updated At** | YYYY-MM-DD |

## Context

Descreva em poucas linhas por que esta task existe, qual parte da arquitetura ela implementa e qual problema técnico ela resolve.

## Objectives

Legenda de status:

- `[ ]` Pendente
- `[~]` Em andamento
- `[x]` Bloqueado
- `[✓]` Concluido

- [ ] Objetivo técnico 1.
- [~] Objetivo técnico 2 em andamento.
- [x] Objetivo técnico 3 bloqueado por dependência externa.
- [✓] Objetivo técnico 4 concluido.

## Non-Goals

- Fora de escopo 1.
- Fora de escopo 2.

## Stage Boundaries

Esta implementação deve se limitar ao domínio descrito em `Stage Ref`. Caso a task precise tocar outro stage, registre a dependência em **Dependencies** antes de implementar.

## Dependencies

- Nenhuma.

## Inputs & Contracts

- **Inputs**: eventos, payloads, requests, tabelas ou configs consumidas.
- **Outputs**: respostas, eventos, registros persistidos ou side effects esperados.
- **Schemas**: modelos Pydantic, migrations, contratos JSON ou tool schemas afetados.

## Constraints & Rules

1. **Scope Control**: A implementação deve se limitar estritamente ao domínio definido no Stage de referência.
2. **State Management**: Toda alteração de estado deve ser persistida via Redis ou PostgreSQL conforme a arquitetura.
3. **Tenant Isolation**: Toda query tenant-scoped deve exigir `tenant_id` e respeitar RLS quando aplicável.
4. **Error Handling**: Falhas em chamadas externas devem gerar logs estruturados e retries quando aplicável.
5. **Typing**: Uso obrigatório de type hints e validação via Pydantic nas fronteiras de entrada/saída.
6. **Security**: Secrets, API keys e auth headers nunca devem aparecer em logs, traces ou payloads não criptografados.
7. **Observability**: Fluxos relevantes devem emitir métricas, logs estruturados ou traces conforme o stage.

## Implementation Checklist

- [ ] Ler `Stage Ref` e confirmar limites de escopo.
- [ ] Identificar tabelas, configs, schemas e endpoints afetados.
- [ ] Setup de ambiente/infra necessário.
- [ ] Implementação da lógica core.
- [ ] Validação de schema/contrato.
- [ ] Tratamento de erros e retries, se aplicável.
- [ ] Logs, métricas ou traces necessários.
- [ ] Testes de unidade.
- [ ] Testes de integração ou fluxo end-to-end.
- [ ] Atualização de documentação, se necessário.

## Acceptance Criteria

- [ ] Critério verificável 1.
- [ ] Critério verificável 2.
- [ ] Critério verificável 3.
- [ ] Não há regressão conhecida nos fluxos relacionados.

## Verification

Comandos, cenários ou evidências usados para validar a entrega:

```bash
# Exemplo:
# pytest tests/path/to/test_file.py
```

## Risks & Rollback

- **Risks**: riscos técnicos, operacionais ou de segurança.
- **Rollback**: como desativar, reverter ou mitigar a mudança.

## Execution Log

- `[YYYY-MM-DD HH:MM]`: Ação realizada ou evento técnico detectado.
- `[YYYY-MM-DD HH:MM]`: Decisão de arquitetura ou erro encontrado.
