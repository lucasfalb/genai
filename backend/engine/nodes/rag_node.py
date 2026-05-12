import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncConnection

from engine.ai_provider import AIProviderResolver
from engine.state import AgentState
from engine.tracer import tracer
from rag.embedder import EmbedderError, OpenAIEmbedder
from rag.retriever import TenantRetriever

logger = logging.getLogger("engine.nodes.rag_node")


def create_rag_node(connection: AsyncConnection, *, retriever: TenantRetriever | None = None):
    override = retriever
    cached: dict = {"retriever": None, "tenant_id": None}

    async def _get_retriever(tenant_id: str) -> TenantRetriever:
        if override is not None:
            return override
        if cached["retriever"] is not None and cached["tenant_id"] == tenant_id:
            return cached["retriever"]
        api_key = await AIProviderResolver(connection).resolve_embedding_api_key(
            tenant_id=UUID(tenant_id)
        )
        if not api_key:
            raise EmbedderError("No OpenAI API key available for embeddings")
        embedder = OpenAIEmbedder(api_key=api_key)
        retr = TenantRetriever(db=connection, embedder=embedder)
        cached["retriever"] = retr
        cached["tenant_id"] = tenant_id
        return retr

    async def rag_node(state: AgentState) -> AgentState:
        rag_scope = state.get("rag_scope") or []
        if not rag_scope:
            logger.info("RAG node skipped: rag_scope empty | instance=%s", state.get("instance_id"))
            return {"retrieved_chunks": []}

        messages = state.get("messages") or []
        last_user = next(
            (m for m in reversed(messages) if m.get("role") == "user" and m.get("content")),
            None,
        )
        query = (last_user or {}).get("content", "")
        if not query:
            logger.info("RAG node skipped: no user message | instance=%s", state.get("instance_id"))
            return {"retrieved_chunks": []}

        tenant_id = state.get("tenant_id", "")
        try:
            retr = await _get_retriever(tenant_id)
            with tracer.start_as_current_span(
                "rag.retrieve",
                attributes={
                    "collection_count": len(rag_scope),
                    "query_length": len(query),
                },
            ) as span:
                chunks = await retr.retrieve(
                    query=query,
                    tenant_id=tenant_id,
                    rag_scope=rag_scope,
                )
                span.set_attribute("chunk_count", len(chunks))
                scores = [c.get("score") for c in chunks if isinstance(c, dict) and c.get("score") is not None]
                if scores:
                    span.set_attribute("max_score", max(scores))
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {str(exc)[:240]}"
            logger.warning(
                "RAG retrieval failed | tenant=%s instance=%s error=%s",
                tenant_id, state.get("instance_id"), error_msg,
            )
            return {"retrieved_chunks": [], "rag_error": error_msg}
        retriever_for_usage = retr

        embed_usage = getattr(retriever_for_usage, "last_usage", None) or {"prompt_tokens": 0, "total_tokens": 0}
        current_usage = state.get("token_usage") or {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "llm_calls": 0,
            "per_call": [],
            "embedding_tokens": 0,
            "embedding_calls": 0,
        }
        next_usage = {
            **current_usage,
            "embedding_tokens": current_usage.get("embedding_tokens", 0) + embed_usage.get("prompt_tokens", 0),
            "embedding_calls": current_usage.get("embedding_calls", 0) + (1 if embed_usage.get("prompt_tokens", 0) else 0),
        }

        if not chunks:
            logger.info(
                "RAG returned no chunks | tenant=%s instance=%s scope=%s query=%r",
                state.get("tenant_id"), state.get("instance_id"), rag_scope, query[:120],
            )
            return {"retrieved_chunks": [], "token_usage": next_usage}

        context_lines = ["\n\n### Contexto Relevante"]
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("source") or "unknown"
            text = chunk["text"]
            context_lines.append(f"\n[{i}] (fonte: {source}): {text}")
        context_section = "".join(context_lines)

        system_prompt = state.get("system_prompt", "")
        constraints_marker = "### Restrições"
        if constraints_marker in system_prompt:
            system_prompt = system_prompt.replace(
                constraints_marker, context_section + "\n\n" + constraints_marker, 1
            )
        else:
            system_prompt += context_section

        return {"retrieved_chunks": chunks, "system_prompt": system_prompt, "token_usage": next_usage}

    return rag_node
