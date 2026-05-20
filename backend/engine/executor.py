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
from engine.handoff import HandoffSanitizer, HandoffSummarizer, build_handoff_messages
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
    event_queue: asyncio.Queue
    trace_repository: RunTraceRepository
    started_at: datetime
    _closed: bool = field(default=False, init=False)

    async def events(self):
        try:
            yield self.user_event
            buffer = ""
            graph_steps: list[dict] = []

            while True:
                if self.graph_task.done() and self.event_queue.empty():
                    break
                try:
                    item = await asyncio.wait_for(self.event_queue.get(), timeout=0.25)
                except asyncio.TimeoutError:
                    continue
                if item is _STREAM_SENTINEL:
                    break

                if isinstance(item, str):
                    buffer += item
                    yield ChatEvent(
                        event="assistant.delta",
                        session_id=self.session_id,
                        content=buffer,
                    )
                elif isinstance(item, dict):
                    _type = item.get("_type")
                    if _type == "node.started":
                        yield ChatEvent(
                            event="graph.node.started",
                            session_id=self.session_id,
                            metadata={
                                "name": item["name"],
                                "step": item["step"],
                                "triggers": item.get("triggers"),
                            },
                        )
                    elif _type == "node.completed":
                        step_record = {k: v for k, v in item.items() if k != "_type"}
                        graph_steps.append(step_record)
                        yield ChatEvent(
                            event="graph.node.completed",
                            session_id=self.session_id,
                            metadata={
                                "name": item["name"],
                                "step": item["step"],
                                "duration_ms": item["duration_ms"],
                                "error": item.get("error"),
                            },
                        )
                    elif _type == "handoff":
                        yield ChatEvent(
                            event="graph.handoff",
                            session_id=self.session_id,
                            metadata={
                                "source_instance_id": item["source_instance_id"],
                                "target_instance_id": item["target_instance_id"],
                                "target_name": item["target_name"],
                                "reason": item["reason"],
                            },
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
                graph_steps=graph_steps,
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

            event_queue: asyncio.Queue = asyncio.Queue()

            def delta_sink(chunk: str) -> None:
                event_queue.put_nowait(chunk)

            graph = create_base_graph(connection=self.connection)

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
                        pending_tasks: dict[str, dict] = {}

                        async def _stream_graph(g, s) -> dict:
                            local_final: dict = {}
                            async for mode, payload in g.astream(s, stream_mode=["values", "debug"]):
                                if mode == "debug":
                                    event_type = payload.get("type")
                                    if event_type == "task":
                                        task_payload = payload.get("payload") or {}
                                        task_id = task_payload.get("id")
                                        started_at_ts = payload.get("timestamp")
                                        entry = {
                                            "task_id": task_id,
                                            "name": task_payload.get("name"),
                                            "step": payload.get("step"),
                                            "started_at": started_at_ts,
                                            "triggers": task_payload.get("triggers"),
                                        }
                                        if task_id:
                                            pending_tasks[task_id] = entry
                                        event_queue.put_nowait({
                                            "_type": "node.started",
                                            "name": entry["name"],
                                            "step": entry["step"],
                                            "started_at": started_at_ts,
                                            "triggers": entry["triggers"],
                                        })
                                    elif event_type == "task_result":
                                        task_payload = payload.get("payload") or {}
                                        task_id = task_payload.get("id")
                                        pending = pending_tasks.pop(task_id, None)
                                        ended_at_ts = payload.get("timestamp")
                                        duration_ms = 0
                                        if pending:
                                            try:
                                                t_s = datetime.fromisoformat(
                                                    (pending["started_at"] or "").replace("Z", "+00:00")
                                                )
                                                t_e = datetime.fromisoformat(
                                                    (ended_at_ts or "").replace("Z", "+00:00")
                                                )
                                                duration_ms = max(0, int((t_e - t_s).total_seconds() * 1000))
                                            except Exception:
                                                duration_ms = 0
                                        event_queue.put_nowait({
                                            "_type": "node.completed",
                                            "name": (pending or {}).get("name") or task_payload.get("name"),
                                            "step": (pending or {}).get("step"),
                                            "started_at": (pending or {}).get("started_at"),
                                            "ended_at": ended_at_ts,
                                            "duration_ms": duration_ms,
                                            "triggers": (pending or {}).get("triggers"),
                                            "error": task_payload.get("error"),
                                        })
                                elif mode == "values":
                                    local_final = payload
                            return local_final

                        final_state = await _stream_graph(graph, state)

                        # If the source agent decided to hand off, run the target agent
                        if final_state.get("handoff_target"):
                            target_id = UUID(str(final_state["handoff_target"]))
                            source_links = state.get("linked_agents") or []
                            link_cfg = next(
                                (l for l in source_links if l["target_instance_id"] == str(target_id)),
                                {},
                            )
                            context_policy = link_cfg.get("context_policy") or {}
                            reason = str(final_state.get("handoff_summary") or "Conversation transferred to specialist.")

                            summary = await HandoffSummarizer().summarize(
                                messages=state["messages"],
                                reason=reason,
                                source_instance_id=str(instance_id),
                                target_instance_id=str(target_id),
                                custom_instructions=link_cfg.get("handoff_instructions"),
                            )
                            sanitized = HandoffSanitizer.keep_recent_conversation(
                                state["messages"],
                                max_messages=int(context_policy.get("max_messages") or 8),
                            )
                            handoff_msgs = build_handoff_messages(
                                summary=summary,
                                sanitized_messages=sanitized,
                                context_policy=context_policy,
                            )

                            event_queue.put_nowait({
                                "_type": "handoff",
                                "source_instance_id": str(instance_id),
                                "target_instance_id": str(target_id),
                                "target_name": link_cfg.get("target_name", ""),
                                "reason": reason,
                            })

                            target_state = await RunBootstrap(self.connection).prepare(
                                tenant_id=tenant_id,
                                instance_id=target_id,
                                session_id=UUID(str(state["session_id"])),
                                channel=channel,
                            )
                            target_state["messages"] = handoff_msgs
                            target_graph = create_base_graph(connection=self.connection)
                            final_state = await _stream_graph(target_graph, target_state)
                            final_state["_handoff_target"] = str(target_id)
                            final_state["_handoff_target_name"] = link_cfg.get("target_name", "")
                            final_state["_handoff_context"] = {
                                "reason": reason,
                                "source_instance_id": str(instance_id),
                                "target_instance_id": str(target_id),
                                "summary": summary.model_dump(mode="json"),
                                "sanitized_messages": sanitized,
                                "handoff_messages": handoff_msgs,
                            }

                        span_context = span.get_span_context()
                        if span_context.is_valid:
                            final_state["_otel_trace_id"] = otel_trace.format_trace_id(span_context.trace_id)

                        return final_state
                    finally:
                        delta_sink_var.reset(token)
                        event_queue.put_nowait(_STREAM_SENTINEL)

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
                event_queue=event_queue,
                trace_repository=RunTraceRepository(self.connection),
                started_at=started_at,
            )
        except Exception:
            await self.lock.release(tenant_id=tenant_id, session_id=session.id, run_id=run_id)
            raise

    @staticmethod
    def encode_sse(event: ChatEvent) -> str:
        return f"data: {json.dumps(event.model_dump(mode='json'), separators=(',', ':'))}\n\n"
