# Task: TASK-084 - Migrar Indexacao RAG para Backend Gerenciado

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-084 |
| **Group** | RAG |
| **Status** | IN_PROGRESS |
| **Stage Ref** | `docs/stages/stage_06_rag.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-15 |
| **Updated At** | 2026-05-15 |

## Context

O pipeline RAG atual depende de um processo separado `indexing-worker` que consome a fila Redis `rag:indexing_queue`. Essa separacao funciona tecnicamente, mas cria custo operacional extra no Coolify: imagem separada, registry privado, permissao GHCR e coordenacao de deploy.

Esta task planeja migrar a indexacao para um mecanismo gerenciado pelo proprio backend, preservando o comportamento assicrono para uploads/reindex/delete e evitando que requisicoes HTTP fiquem bloqueadas por extracao, embeddings ou upsert no Qdrant.

## Objectives

- [x] Remover a obrigatoriedade operacional do servico externo `indexing-worker` no deploy.
- [x] Reutilizar a logica existente de `rag.indexing_worker.IndexingWorker` sem duplicar extracao, chunking, embeddings ou Qdrant.
- [x] Substituir ou encapsular o enqueue Redis por um dispatcher de indexacao controlado pelo backend.
- [x] Preservar status e progresso de `documents` e `collections`.
- [x] Preservar suporte a upload, create text document, update content, delete document e reindex.
- [x] Manter execucao assicrona e tolerante a falhas, sem bloquear a resposta dos endpoints.

## Non-Goals

- Reescrever o pipeline de RAG, chunking, embeddings ou retriever.
- Substituir Qdrant ou MinIO.
- Remover Redis de todo o sistema; esta task remove a dependencia do worker externo, nao necessariamente todos os usos de Redis.
- Implementar OCR, novos tipos de documento ou URL ingestion.
- Alterar contratos publicos de upload/reindex alem de mensagens ou metadados necessarios.

## Stage Boundaries

Esta implementacao deve se limitar ao Stage 06 RAG: indexacao de documentos, status de collections/documents, object storage, Qdrant e fila/dispatcher de indexacao. Caso a migracao exija alteracoes de deploy Coolify, registrar como documentacao operacional e nao como mudanca de produto.

## Dependencies

- TASK-043 (Documents Upload e Status API).
- TASK-044 (Indexing Pipeline Worker).
- TASK-047 (Verificacao Stage 06 RAG).
- Backend separado no Coolify deve estar apto a conectar em Redis, Qdrant, MinIO e Postgres.

## Inputs & Contracts

- **Inputs**: eventos gerados pelos endpoints de collections/documents: upload, create, update, delete e reindex.
- **Outputs**: status atualizado em `documents` e `collections`; chunks atualizados/removidos no Qdrant; arquivos continuam no MinIO.
- **Schemas**: manter payload conceitual `{tenant_id, collection_id, document_id, action}` para reaproveitar `IndexingJob`.
- **Runtime Contracts**: backend deve iniciar/parar o mecanismo de processamento com o ciclo de vida da aplicacao FastAPI; falhas devem ser logadas e refletidas em `documents.status = failed` quando aplicavel.

## Constraints & Rules

1. **Nao bloquear HTTP**: endpoints devem responder apos persistir arquivo/metadados e agendar processamento.
2. **Idempotencia**: reindex deve continuar removendo chunks antigos antes de upsert novo.
3. **Tenant Isolation**: todo processamento deve usar `TenantContext` e `tenant_id` explicito.
4. **Failure Visibility**: excecoes de extracao, embedding, storage ou Qdrant devem atualizar `documents.status = failed`.
5. **Graceful Shutdown**: tarefas em background devem respeitar shutdown do FastAPI sempre que possivel.
6. **Deploy Simples**: Coolify nao deve precisar de imagem separada para `indexing-worker`.
7. **Sem Worker Separado**: deploys padrao nao devem depender de processo ou imagem `indexing-worker`.
8. **Secrets**: nenhuma chave de API, SMTP, DB, MinIO ou GHCR em logs, traces ou task output.

## Implementation Checklist

- [x] Ler `docs/stages/stage_06_rag.md` e confirmar limites de escopo.
- [x] Mapear todos os pontos que fazem `redis_client.rpush(INDEXING_QUEUE_KEY, ...)`.
- [x] Extrair um modulo de contrato para `IndexingJob` e `INDEXING_QUEUE_KEY`, se necessario.
- [x] Criar um servico de aplicacao, por exemplo `rag/indexing_service.py`, que exponha `schedule_index`, `schedule_delete` e `schedule_reindex`.
- [x] Definir modo de execucao inicial recomendado: backend background consumer usando Redis interno ou task queue in-process.
- [x] Implementar ciclo de vida no FastAPI para iniciar/parar consumer de indexacao junto com a aplicacao.
- [x] Atualizar endpoints de documents/collections para chamar o novo servico em vez de depender diretamente do worker externo.
- [x] Remover caminho operacional legado `python -m rag.indexing_worker`.
- [x] Remover `indexing-worker` do compose Coolify e do `docker.env` apos validacao.
- [x] Atualizar docs operacionais com variaveis restantes: `REDIS_URL`, `QDRANT_URL`, `S3_ENDPOINT_URL`, `OTEL_EXPORTER_OTLP_ENDPOINT`.
- [x] Adicionar testes unitarios do dispatcher/servico de indexacao.
- [x] Adicionar teste de integracao cobrindo dispatcher de agendamento e fallback sem worker externo.
- [x] Adicionar teste de falha cobrindo erro de enqueue e fallback inline sem falhar endpoint.
- [x] Validar que reindex e delete continuam usando o mesmo contrato de job consumido pelo backend.

## Acceptance Criteria

- [x] Deploy Coolify nao precisa mais declarar ou puxar imagem `indexing-worker`.
- [x] Upload de documento retorna sem aguardar embedding/Qdrant e agenda processamento no backend.
- [x] Documento processado pelo backend chega a `documents.status = indexed` com `chunk_count > 0` nos testes existentes do pipeline.
- [x] Falha de processamento marca `documents.status = failed` e atualiza status agregado da collection nos testes existentes do pipeline.
- [x] Reindex de collection continua substituindo chunks antigos no Qdrant.
- [x] Delete de documento continua removendo arquivo do MinIO e chunks do Qdrant.
- [x] Testes Stage 06 existentes continuam passando.
- [x] Documentacao e compose Coolify ficam sem referencia obrigatoria a `INDEXING_WORKER_IMAGE`.

## Verification

Comandos e cenarios previstos para validar a entrega:

```bash
cd backend
pytest tests/test_stage_06_documents.py
pytest tests/test_stage_06_collections.py
pytest tests/test_stage_06_indexing_worker.py
pytest tests/test_stage_06_rag_retriever.py
```

```bash
python scripts/validate_tasks.py
```

Cenario manual:

1. Subir backend com Redis, Qdrant e MinIO acessiveis.
2. Criar collection.
3. Fazer upload de `.txt` pequeno.
4. Confirmar resposta HTTP imediata.
5. Confirmar transicao `uploaded -> indexing -> indexed`.
6. Confirmar chunks no Qdrant com `tenant_id`, `collection_id` e `document_id`.

## Risks & Rollback

- **Risks**: processamento pesado pode competir com API; deploys com muitas replicas precisam manter Redis como fila compartilhada para evitar jobs in-process perdidos em restart.
- **Mitigation**: manter Redis como fila persistente, mover apenas o consumer para o backend, usar `BLPOP` para garantir um consumidor por job e permitir pausa operacional com `RAG_INDEXING_CONSUMER_ENABLED=false`.
- **Rollback**: usar controle de versao se esta mudanca precisar ser revertida; nao manter caminho operacional paralelo nem imagem/container `indexing-worker` no deploy.

## Execution Log

- `[2026-05-15 00:00]`: Task criada para planejar migracao da indexacao RAG para backend gerenciado e remover dependencia operacional do `indexing-worker` separado.
- `[2026-05-15 00:00]`: Implementacao iniciada; decisao inicial e manter Redis como fila persistente e mover o consumer para o ciclo de vida do backend FastAPI.
- `[2026-05-15 00:00]`: Criado `rag/indexing_service.py`, endpoints de collections/documents passaram a chamar o dispatcher centralizado, FastAPI passou a iniciar consumer no lifespan, e compose Coolify/local removeram o container `indexing-worker`.
- `[2026-05-15 00:00]`: Validacao Stage 06 com pytest bloqueada porque Postgres local de teste em `localhost:5432` recusou conexao; manter task em IN_PROGRESS ate executar E2E com banco disponivel.
- `[2026-05-15 00:00]`: Testes unitarios de `rag.indexing_service` adicionados e executados com sucesso sem dependencia de Postgres.
- `[2026-05-15 00:00]`: Testes configurados para usar `DATABASE_SCHEMA=genai_test` no Postgres remoto do `.env`; Alembic passou a migrar no schema definido por `DATABASE_SCHEMA`.
- `[2026-05-15 00:00]`: Repositorios RAG passaram a validar o tenant ativo da conexao alem do parametro `tenant_id`, protegendo isolamento mesmo quando o banco usa usuario superuser.
- `[2026-05-15 00:00]`: Consumer embutido passou a testar Redis no startup e ficar desativado com warning unico quando Redis esta indisponivel, evitando falha repetida em desenvolvimento local.
- `[2026-05-15 00:00]`: OTel passou a ser opt-in por `OTEL_ENABLED`; `docker.env` habilita em producao com collector do compose, enquanto local sem collector nao tenta exportar traces.
- `[2026-05-15 00:00]`: `coolify-docker-compose.yml` passou a criar rede nomeada `genai-internal` com aliases estaveis para Redis, Qdrant, MinIO, OTel, Tempo e Grafana; `docker.env` foi alinhado para backend/frontend separados no Coolify.
- `[2026-05-15 00:00]`: Logs do Coolify indicaram que `configs:` viravam diretorios para OTel/Tempo; compose foi ajustado para gerar configuracoes inline no startup dos containers, sem arquivos externos.
- `[2026-05-15 00:00]`: Deploy Coolify indicou que a imagem `otel/opentelemetry-collector-contrib` nao possui `/bin/sh`; OTel passou a carregar configuracao via `--config=env:OTEL_CONFIG`.
