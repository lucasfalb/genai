# Task: TASK-073 - Collections RAG Management UI

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-073 |
| **Group** | FRONTEND |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_09_frontend.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | MEDIUM |
| **Owner** | Unassigned |
| **Created At** | 2026-05-08 |
| **Updated At** | 2026-05-08 |

## Context

Collections agrupam documentos para RAG. A UI deve existir dentro do app tenant-scoped, mas nao como item direto do menu lateral. O acesso principal fica pela secao Knowledge do detalhe do Agent e por rota direta `/app/{tenantSlug}/collections`.

## Objectives

- [x] Criar cliente tipado `frontend/src/lib/api/collections.ts`.
- [x] Implementar listagem tenant-scoped em `/app/{tenantSlug}/collections`.
- [x] Implementar criacao e edicao de collection via dialog reutilizavel.
- [x] Implementar detalhe em `/app/{tenantSlug}/collections/{id}` com status, metricas e placeholder de documentos.
- [x] Manter redirects de compatibilidade `/knowledge` para `/collections`.

## Non-Goals

- Nao implementar upload ou gestao individual de documentos, pois ainda nao ha endpoint frontend contratado para documentos.
- Nao implementar polling de indexacao nesta entrega.
- Nao adicionar Knowledge ao menu lateral.

## Stage Boundaries

Apenas frontend para CRUD de collections usando os endpoints `tenant-collections` existentes.

## Dependencies

- TASK-068
- TASK-076

## Inputs & Contracts

- `GET /tenant/collections`
- `POST /tenant/collections`
- `GET /tenant/collections/{id}`
- `PATCH /tenant/collections/{id}`
- `DELETE /tenant/collections/{id}`

Rotas frontend:

- `/app/{tenantSlug}/collections`
- `/app/{tenantSlug}/collections/{id}`
- `/app/{tenantSlug}/knowledge` -> redirect para `/collections`
- `/app/{tenantSlug}/knowledge/{id}` -> redirect para `/collections/{id}`

Componentes:

- `frontend/src/lib/components/CollectionDialog.svelte`
- `frontend/src/lib/components/IndexingStatusBadge.svelte`

## Constraints & Rules

1. Collections nao aparecem como item do aside.
2. A secao Knowledge do detalhe de Agent deve apontar para `/collections`.
3. Nome de collection exige ao menos 2 caracteres no frontend.
4. Delete exige confirmacao explicita.
5. Placeholder de documentos deve deixar claro que upload/gestao de documentos vira em task futura.

## Implementation Checklist

- [x] Criar `frontend/src/lib/api/collections.ts` com os 5 metodos.
- [x] Criar `CollectionDialog.svelte`.
- [x] Criar `IndexingStatusBadge.svelte`.
- [x] Criar SSR loader e page de `/collections`.
- [x] Criar SSR loader e page de `/collections/{id}`.
- [x] Criar redirects `/knowledge` e `/knowledge/{id}`.
- [x] Adicionar link Knowledge dentro do detalhe do Agent.

## Acceptance Criteria

- [x] Listagem exibe collections do tenant ativo.
- [x] Criacao adiciona collection na lista sem reload manual.
- [x] Detalhe exibe status, document_count, indexed_count, failed_count e last_indexed_at.
- [x] Edicao atualiza estado local.
- [x] Delecao remove collection apos confirmacao e volta para a listagem.
- [x] Rotas `/knowledge*` redirecionam para `/collections*`.
- [x] Menu lateral nao exibe Knowledge.

## Verification

```bash
cd frontend
npm run check
npm run test:unit
cd ..
python scripts/validate_tasks.py
```

## Risks & Rollback

- **Risco**: documentos ainda nao aparecem porque a UI de documentos nao existe. **Mitigacao**: placeholder explicito na pagina de detalhe.
- **Risco**: usuario procurar Knowledge no menu lateral. **Mitigacao**: acesso pela pagina do Agent e redirects de compatibilidade.
- **Rollback**: remover rotas `/collections*`, componentes e cliente `collections.ts`.

## Execution Log

- `[2026-05-08 00:00]`: Task criada.
- `[2026-05-08 20:35]`: Collections UI implementada em `/app/{tenant}/collections`, com detalhe, dialog de criacao/edicao, status badge, redirects de `/knowledge` e link Knowledge dentro do detalhe de Agent.
