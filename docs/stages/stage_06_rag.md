# Stage 06 — RAG, Knowledge Base e Retrieval

_Fonte canônica: [`../platform_technical_spec.md`](../platform_technical_spec.md). Este stage reorganiza o conteúdo técnico sem substituir a especificação completa._

## Objetivo

Definir ingestão de documentos, status de indexação, Qdrant, embeddings, escopo por instância e lógica de recuperação com RBAC.

## Tabelas Relevantes

```sql
-- Coleções de documentos para RAG
CREATE TABLE collections (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  name            TEXT NOT NULL,
  description     TEXT,
  indexing_status TEXT NOT NULL DEFAULT 'empty',  -- empty | indexing | ready | partial | failed
  indexing_progress FLOAT NOT NULL DEFAULT 0,     -- 0.0 a 1.0
  document_count  INTEGER NOT NULL DEFAULT 0,
  indexed_count   INTEGER NOT NULL DEFAULT 0,
  failed_count    INTEGER NOT NULL DEFAULT 0,
  last_indexed_at TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Documentos enviados para RAG
CREATE TABLE documents (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  collection_id   UUID NOT NULL REFERENCES collections(id),
  filename        TEXT NOT NULL,
  source_type     TEXT NOT NULL,       -- upload | url | api
  status          TEXT NOT NULL DEFAULT 'uploaded',  -- uploaded | indexing | indexed | failed
  chunk_count     INTEGER NOT NULL DEFAULT 0,
  error_message   TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  indexed_at      TIMESTAMPTZ
);
```

### Vector Store (Qdrant)

Coleções compartilhadas por plan/modelo, filtradas por payload `tenant_id` e `collection_id`. Coleções dedicadas apenas em Enterprise.
Qdrant armazena vetores e payload JSON dos chunks indexados; os arquivos originais de upload ficam em object storage S3-compatible. No ambiente local, esse storage e fornecido por MinIO.

```json
{
  "tenant_id": "abc123",
  "collection_id": "uuid-da-colecao",
  "document_id": "uuid-do-documento",
  "chunk_index": 3,
  "embedding_model": "text-embedding-3-large",
  "text": "conteúdo do chunk..."
}
```

---

## 7. RAG e Knowledge Base

### Pipeline de indexação

```
Upload de documento (PDF/DOCX/URL)
   ↓
documents.status = uploaded
collections.indexing_status = indexing
   ↓
Consumer de indexação em background gerenciado pelo backend
   ↓
Extração de texto → Chunking → Embedding
   ↓
Qdrant (payload: tenant_id, collection_id, document_id, chunk_index)
   ↓
documents.status = indexed | failed
collections.indexing_status = ready | partial | failed
```

### Status de indexação

O `rag_scope` define quais coleções a instância pode consultar, mas a disponibilidade real depende do `indexing_status` da coleção. Enquanto uma coleção está em `indexing`, a skill de RAG pode operar parcialmente com documentos já indexados, mas o frontend deve deixar claro que a base nova ainda não está 100% disponível.

Estados:

- `empty`: coleção criada, sem documentos indexáveis.
- `indexing`: há documentos em processamento.
- `ready`: todos os documentos válidos foram indexados.
- `partial`: parte dos documentos falhou, mas existe conteúdo pesquisável.
- `failed`: nenhum documento novo ficou pesquisável.

O backend expõe `indexing_progress`, `document_count`, `indexed_count`, `failed_count` e `last_indexed_at` para a tela de Knowledge Base e para a aba RAG da instância. Uploads grandes devem ser processados por consumer em background gerenciado pelo backend, com atualização incremental de progresso. Deploys padrao nao precisam de um container `indexing-worker` separado.

O backend tambem expoe `POST /tenant/collections/{collection_id}/reindex` para reenfileirar todos os documentos de uma collection. O reindex reseta os documents para `uploaded`, marca a collection como `indexing` e o consumer de indexacao remove os chunks antigos do document no Qdrant antes do novo upsert.

### Retriever com RBAC

```python
# rag/retriever.py

class TenantRetriever:
    async def retrieve(
        self,
        query: str,
        tenant_id: str,
        rag_scope: list[str],  # collection_ids habilitadas na instância
        top_k: int = 5,
    ) -> list[dict]:
        if not rag_scope:
            return []

        ready_scope = await self.db.get_searchable_collections(
            tenant_id=tenant_id,
            collection_ids=rag_scope,
            allowed_statuses=["ready", "partial", "indexing"],
        )
        if not ready_scope:
            return []

        embedding = await self.embedder.embed(query)

        results = await self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=embedding,
            query_filter={
                "must": [
                    {"key": "tenant_id", "match": {"value": tenant_id}},
                    {"key": "collection_id", "match": {"any": ready_scope}},
                    {"key": "document_status", "match": {"value": "indexed"}},
                ]
            },
            limit=top_k,
        )

        return [
            {
                "text": r.payload["text"],
                "source": r.payload.get("source"),
                "score": r.score,
            }
            for r in results
        ]
```

---

## Jornada de UI Relacionada

```text
4. Aba "RAG"
   → Selecionar quais coleções de documentos ficam disponíveis
   → Ver status por coleção: Empty, Indexing, Ready, Partial ou Failed
   → Quando houver Indexing/Partial, exibir progresso e aviso de que a skill de RAG ainda não usa 100% da base nova
```
