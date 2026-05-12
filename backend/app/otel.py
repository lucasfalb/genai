import logging
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.config import settings

logger = logging.getLogger("genai.otel")
_otel_initialized = False


def setup_otel(app) -> None:
    global _otel_initialized
    if _otel_initialized:
        logger.debug("OTel SDK already initialized")
        return

    otel_endpoint = _normalize_endpoint(settings.otel_exporter_otlp_endpoint)
    service_name = settings.otel_service_name
    env_name = settings.genai_env
    extra_attrs = settings.otel_resource_attributes

    resource_attrs = {
        "service.name": service_name,
        "deployment.environment": env_name,
    }
    service_version = _service_version()
    if service_version:
        resource_attrs["service.version"] = service_version

    for pair in extra_attrs.split(","):
        pair = pair.strip()
        if "=" in pair:
            k, v = pair.split("=", 1)
            resource_attrs[k.strip()] = v.strip()

    resource = Resource.create(resource_attrs)
    tracer_provider = TracerProvider(resource=resource)

    try:
        exporter = OTLPSpanExporter(endpoint=otel_endpoint, insecure=True)
        span_processor = BatchSpanProcessor(exporter)
        tracer_provider.add_span_processor(span_processor)
        logger.info("OTel exporter configured for %s", otel_endpoint)
    except Exception as exc:
        logger.warning("OTel exporter unavailable (%s); traces will be dropped", exc)

    trace.set_tracer_provider(tracer_provider)

    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumented")
    except Exception as exc:
        logger.warning("FastAPI instrumentation failed: %s", exc)

    for inst_cls, name in [
        (AsyncPGInstrumentor, "asyncpg"),
        (RedisInstrumentor, "redis"),
        (HTTPXClientInstrumentor, "httpx"),
    ]:
        try:
            inst_cls().instrument()
            logger.info("%s instrumented", name)
        except Exception as exc:
            logger.warning("%s instrumentation failed: %s", name, exc)

    _otel_initialized = True
    logger.info("OTel SDK initialized")


def _service_version() -> str | None:
    try:
        return version("genai-backend")
    except PackageNotFoundError:
        return None


def _normalize_endpoint(endpoint: str) -> str:
    if endpoint.startswith("otel-collector:") and not _running_in_container():
        normalized = f"http://localhost:{endpoint.rsplit(':', 1)[1]}"
        logger.warning(
            "OTel endpoint %s points to Docker DNS outside a container; using %s",
            endpoint,
            normalized,
        )
        return normalized

    parsed = urlparse(endpoint)
    host = parsed.hostname
    if host != "otel-collector" or _running_in_container():
        return endpoint

    port = parsed.port or 4317
    netloc = f"localhost:{port}"
    normalized = urlunparse((parsed.scheme or "http", netloc, parsed.path, "", "", ""))
    logger.warning(
        "OTel endpoint %s points to Docker DNS outside a container; using %s",
        endpoint,
        normalized,
    )
    return normalized


def _running_in_container() -> bool:
    return Path("/.dockerenv").exists()
