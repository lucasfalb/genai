# Task: TASK-044 - Indexing Pipeline Worker

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-044 |
| **Group** | RAG |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_06_rag.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Documentos enviados ficam com status `uploaded` ate o worker de indexacao processar. Este worker consome a fila Redis `rag:indexing_queue`, extrai texto, divide em chunks, gera embeddings e salva no Qdrant com payload de filtro por `tenant_id` e `collection_id`.

## Objectives

- [ ] Implementar worker em `rag/indexing_worker.py` que consome `rag:indexing_queue`.
- [ ] Extrair texto de PDF (`pypdf`), DOCX (`python-docx`) e TXT.
- [ ] Dividir em chunks com sobreposicao configuravel (default 512 tokens, overlap 64).
- [ ] Gerar embeddings via OpenAI `text-embedding-3-small`.
- [ ] Salvar chunks no Qdrant com payload `{tenant_id, collection_id, document_id, chunk_index, text}`.
- [ ] Atualizar `documents.status`, `documents.chunk_count`, `documents.indexed_at`.
- [ ] Atualizar `collections.indexed_count`, `collections.failed_count`, `collections.indexing_progress`, `collections.indexing_status` e `collections.last_indexed_at`.

## Non-Goals

- Suporte a URLs como source (primeira versao: apenas arquivos locais).
- OCR de PDFs escaneados.
- Fila com retries avancados (RQ/Celery) — Redis BLPOP e suficiente nesta versao.

## Stage Boundaries

Worker de background separado do FastAPI. Nao cria endpoints.

## Dependencies

- TASK-043 (Documents API — publica jobs na fila)

## Inputs & Contracts

- **Inputs**: job `{document_id, tenant_id, collection_id}` da fila `rag:indexing_queue`.
- **Outputs**: chunks no Qdrant, status atualizado em `documents` e `collections`.
- **Schemas**: Qdrant point com payload `{tenant_id, collection_id, document_id, chunk_index, text, embedding_model}`.

## Constraints & Rules

1. `documents.status = indexing` ao iniciar processamento.
2. `documents.status = indexed` com `chunk_count` e `indexed_at` ao concluir.
3. `documents.status = failed` com `error_message` em excecao.
4. Qdrant collection name: `genai_rag` (compartilhada; filtros por payload).
5. `OPENAI_EMBEDDING_API_KEY` e `QDRANT_URL` configurados via settings.
6. Secrets nunca em logs.

## Implementation Checklist

- [ ] Adicionar `pypdf`, `python-docx`, `qdrant-client` ao `pyproject.toml`.
- [ ] Criar `rag/text_extractor.py` com suporte a PDF, DOCX e TXT.
- [ ] Criar `rag/chunker.py` com chunking por tokens.
- [ ] Criar `rag/embedder.py` chamando OpenAI embeddings.
- [ ] Criar `rag/qdrant_client.py` com upsert e delete por `document_id`.
- [ ] Criar `rag/indexing_worker.py` com loop `BLPOP`.
- [ ] Testar pipeline com PDF simples mockando OpenAI e Qdrant.

## Acceptance Criteria

- [ ] Apos worker processar job, `documents.status = indexed` e `chunk_count > 0`.
- [ ] Chunks aparecem no Qdrant com payload correto de `tenant_id` e `collection_id`.
- [ ] Falha de extracao marca `documents.status = failed` com `error_message`.
- [ ] `collections.indexing_status` atualizado para `ready` quando todos os documents estao indexados.

## Verification

```bash
cd backend
pytest tests/test_stage_06_indexing_worker.py
```

## Risks & Rollback

- **Risks**: custo de embeddings por documento; latencia do Qdrant em volumes grandes.
- **Rollback**: parar worker, marcar documents como `failed`, limpar chunks do Qdrant por `collection_id`.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para pipeline de indexacao background.
