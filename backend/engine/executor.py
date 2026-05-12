import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from opentelemetry import trace as otel_trace
from sqlalchemy.ext.asyncio import AsyncConnection

from app.schemas import ChatEvent

logger = logging.getLogger("engine.executor")
from database.repositories.run_traces import RunTraceRepository
from database.repositories.sessions import SessionRepository
from engine.base_graph import create_base_graph, delta_sink_var
from engine.bootstrap import RunBootstrap
from engine.run_trace import build_run_trace
from engine.session_lock import SessionLock
from engine.tracer import tracer


_STREAM_SENTINEL = object()


@dataclass
class AgentRunStream:
    repository: SessionRepository
    lock: SessionLock
    tenant_id: UUID
    instance_id: UUID
    session_id: UUID
    run_id: str
    channel: str
    user_event: ChatEvent
    user_message: str
    bootstrap_state: dict
    graph_task: asyncio.Task
    delta_queue: asyncio.Queue
    trace_repository: RunTraceRepository
    started_at: datetime
    _closed: bool = field(default=False, init=False)

    async def events(self):
        try:
            yield self.user_event
            buffer = ""
            while True:
                if self.graph_task.done() and self.delta_queue.empty():
                    break
                try:
                    item = await asyncio.wait_for(self.delta_queue.get(), timeout=0.25)
                except asyncio.TimeoutError:
                    continue
                if item is _STREAM_SENTINEL:
                    break
                buffer += str(item)
                yield ChatEvent(
                    event="assistant.delta",
                    session_id=self.session_id,
                    content=buffer,
                )

            run_error: str | None = None
            result_state: dict = {}
            try:
                result_state = await self.graph_task
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                run_error = f"{type(exc).__name__}: {str(exc)[:500]}"
                logger.exception(
                    "Agent run failed | tenant=%s instance=%s run_id=%s",
                    self.tenant_id, self.instance_id, self.run_id,
                )

            response = (result_state.get("final_response") if result_state else None) or buffer or ""
            if not response and run_error:
                response = f"[run failed] {run_error}"
            completed_at = datetime.now(timezone.utc)

            assistant_message = await self.repository.append_message(
                tenant_id=self.tenant_id,
                session_id=self.session_id,
                role="assistant",
                content=response,
                metadata={"engine": "llm", "error": run_error} if run_error else {"engine": "llm"},
            )

            if buffer != response:
                yield ChatEvent(
                    event="assistant.delta",
                    session_id=self.session_id,
                    sequence_no=assistant_message.sequence_no,
                    content=response,
                )

            if run_error and isinstance(result_state, dict):
                result_state.setdefault("run_error", run_error)

            trace = build_run_trace(
                run_id=self.run_id,
                tenant_id=self.tenant_id,
                instance_id=self.instance_id,
                session_id=self.session_id,
                channel=self.channel,
                bootstrap_state=self.bootstrap_state,
                result_state=result_state,
                user_message=self.user_message,
                final_response=response,
                started_at=self.started_at,
                completed_at=completed_at,
                node_timings=self.bootstrap_state.get("_node_timings") or [],
            )
            await self.trace_repository.create(
                run_id=UUID(self.run_id),
                tenant_id=self.tenant_id,
                instance_id=self.instance_id,
                session_id=self.session_id,
                channel=self.channel,
                trace=trace,
                started_at=self.started_at,
                completed_at=completed_at,
            )

            yield ChatEvent(
                event="run.trace",
                session_id=self.session_id,
                sequence_no=assistant_message.sequence_no,
                metadata={"run_id": self.run_id, "trace": trace},
            )
            yield ChatEvent(
                event="run.completed",
                session_id=self.session_id,
                sequence_no=assistant_message.sequence_no,
                metadata={"run_id": self.run_id},
            )
        finally:
            await self.close()

    async def cancel(self) -> None:
        if not self.graph_task.done():
            self.graph_task.cancel()
        await self.close()

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self.lock.release(tenant_id=self.tenant_id, session_id=self.session_id, run_id=self.run_id)


class AgentExecutor:
    def __init__(self, connection: AsyncConnection, *, lock: SessionLock | None = None) -> None:
        self.connection = connection
        self.lock = lock or SessionLock()

    async def run(
        self,
        *,
        tenant_id: UUID,
        instance_id: UUID,
        message: str,
        session_id: UUID | None = None,
        channel: str = "api",
        user_ref: str | None = None,
        metadata: dict | None = None,
    ) -> list[ChatEvent]:
        run = await self.start_stream(
            tenant_id=tenant_id,
            instance_id=instance_id,
            message=message,
            session_id=session_id,
            channel=channel,
            user_ref=user_ref,
            metadata=metadata,
        )
        return [event async for event in run.events()]

    async def start_stream(
        self,
        *,
        tenant_id: UUID,
        instance_id: UUID,
        message: str,
        session_id: UUID | None = None,
        channel: str = "api",
        user_ref: str | None = None,
        metadata: dict | None = None,
    ) -> AgentRunStream:
        repository = SessionRepository(self.connection)
        session = None
        if session_id is not None:
            session = await repository.get_session(tenant_id=tenant_id, session_id=session_id, instance_id=instance_id)
        if session is None:
            session = await repository.create_session(
                tenant_id=tenant_id,
                instance_id=instance_id,
                channel=channel,
                user_ref=user_ref,
                metadata=metadata,
            )

        run_id = str(uuid4())
        await self.lock.acquire(tenant_id=tenant_id, session_id=session.id, run_id=run_id)
        try:
            started_at = datetime.now(timezone.utc)
            state = await RunBootstrap(self.connection).prepare(
                tenant_id=tenant_id,
                instance_id=instance_id,
                session_id=session.id,
                channel=channel,
            )
            user_message = await repository.append_message(
                tenant_id=tenant_id,
                session_id=session.id,
                role="user",
                content=message,
                metadata=metadata,
            )
            state["messages"].append({"role": "user", "content": message})

            node_timings: list[dict] = []
            state["_node_timings"] = node_timings
            delta_queue: asyncio.Queue = asyncio.Queue()

            def delta_sink(chunk: str) -> None:
                delta_queue.put_nowait(chunk)

            graph = create_base_graph(connection=self.connection, node_timings=node_timings)

            async def run_graph():
                token = delta_sink_var.set(delta_sink)
                with tracer.start_as_current_span(
                    "graph.run",
                    attributes={
                        "instance_id": str(instance_id),
                        "tenant_id": str(tenant_id),
                        "model": state.get("model", ""),
                    },
                ) as span:
                    try:
                        result = await graph.ainvoke(state)
                        span_context = span.get_span_context()
                        if span_context.is_valid:
                            result["_otel_trace_id"] = otel_trace.format_trace_id(span_context.trace_id)
                        return result
                    finally:
                        delta_sink_var.reset(token)
                        delta_queue.put_nowait(_STREAM_SENTINEL)

            graph_task = asyncio.create_task(run_graph())

            return AgentRunStream(
                repository=repository,
                lock=self.lock,
                tenant_id=tenant_id,
                instance_id=instance_id,
                session_id=session.id,
                run_id=run_id,
                channel=channel,
                user_event=ChatEvent(
                    event="message.persisted",
                    session_id=session.id,
                    sequence_no=user_message.sequence_no,
                ),
                user_message=message,
                bootstrap_state=state,
                graph_task=graph_task,
                delta_queue=delta_queue,
                trace_repository=RunTraceRepository(self.connection),
                started_at=started_at,
            )
        except Exception:
            await self.lock.release(tenant_id=tenant_id, session_id=session.id, run_id=run_id)
            raise

    @staticmethod
    def encode_sse(event: ChatEvent) -> str:
        return f"data: {json.dumps(event.model_dump(mode='json'), separators=(',', ':'))}\n\n"
