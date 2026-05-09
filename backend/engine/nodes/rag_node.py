import logging

from sqlalchemy.ext.asyncio import AsyncConnection

from engine.state import AgentState
from rag.retriever import TenantRetriever

logger = logging.getLogger("engine.nodes.rag_node")


def create_rag_node(connection: AsyncConnection, *, retriever: TenantRetriever | None = None):
    if retriever is None:
        retriever = TenantRetriever(db=connection)

    async def rag_node(state: AgentState) -> AgentState:
        rag_scope = state.get("rag_scope") or []
        if not rag_scope:
            logger.debug("RAG node skipped: rag_scope empty")
            return {"retrieved_chunks": []}

        messages = state.get("messages") or []
        query = messages[-1].get("content", "") if messages else ""
        if not query:
            logger.debug("RAG node skipped: no user message")
            return {"retrieved_chunks": []}

        chunks = await retriever.retrieve(
            query=query,
            tenant_id=state.get("tenant_id", ""),
            rag_scope=rag_scope,
            top_k=5,
        )

        if not chunks:
            return {"retrieved_chunks": []}

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

        return {"retrieved_chunks": chunks, "system_prompt": system_prompt}

    return rag_node
