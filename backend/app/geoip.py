from functools import lru_cache
from ipaddress import ip_address
from pathlib import Path
from typing import Any

from fastapi import Request

from app.config import settings

try:
    import maxminddb
except ImportError:  # pragma: no cover - optional until dependency is installed
    maxminddb = None  # type: ignore[assignment]


def get_client_ip(request: Request) -> str | None:
    header_names = [name.strip().lower() for name in settings.geoip_ip_header_names.split(",") if name.strip()]
    for name in header_names:
        value = request.headers.get(name)
        if not value:
            continue
        candidate = value.split(",", 1)[0].strip()
        if _is_valid_ip(candidate):
            return candidate
    host = request.client.host if request.client else None
    return host if host and _is_valid_ip(host) else None


def build_request_environment(request: Request) -> dict[str, Any]:
    ip = get_client_ip(request)
    server: dict[str, Any] = {}
    if ip:
        server["ip"] = ip
    user_agent = request.headers.get("user-agent")
    if user_agent:
        server["user_agent"] = user_agent[:512]

    payload: dict[str, Any] = {}
    if server:
        payload["server"] = server
    geo = lookup_geoip(ip)
    if geo:
        payload["geo"] = geo
    return payload


def lookup_geoip(ip: str | None) -> dict[str, Any] | None:
    if not ip or not _is_public_ip(ip):
        return None
    reader = _get_reader()
    if reader is None:
        return None
    try:
        record = reader.get(ip)
    except Exception:
        return None
    if not isinstance(record, dict):
        return None

    geo: dict[str, Any] = {
        "continent": _first_value(record, "continent.names.en", "continent"),
        "continent_code": _first_value(record, "continent_code", "continent.code"),
        "country": _first_value(record, "country_code", "country.iso_code"),
        "country_name": _first_value(record, "country.names.en", "country"),
        "region": _first_subdivision_name(record),
        "city": _first_value(record, "city", "city.names.en"),
        "postal_code": _first_value(record, "postal.code"),
        "latitude": _first_value(record, "location.latitude", "latitude"),
        "longitude": _first_value(record, "location.longitude", "longitude"),
        "timezone": _first_value(record, "location.time_zone", "timezone"),
        "asn": _first_value(record, "asn"),
        "as_name": _first_value(record, "as_name"),
        "as_domain": _first_value(record, "as_domain"),
    }
    return {key: value for key, value in geo.items() if value is not None}


def merge_environment(metadata: dict[str, Any] | None, request: Request) -> dict[str, Any]:
    payload = dict(metadata or {})
    client_env = payload.get("environment") if isinstance(payload.get("environment"), dict) else {}
    request_env = build_request_environment(request)
    environment = _deep_merge(client_env, request_env)
    if environment:
        payload["environment"] = environment
    return payload


@lru_cache(maxsize=1)
def _get_reader():
    if maxminddb is None or not settings.geoip_db_path:
        return None
    db_path = Path(settings.geoip_db_path).expanduser()
    if not db_path.exists():
        return None
    return maxminddb.open_database(str(db_path))


def _first_value(record: dict[str, Any], *paths: str) -> Any:
    for path in paths:
        value = _get_path(record, path)
        if isinstance(value, dict):
            value = value.get("name") or value.get("iso_code") or _get_path(value, "names.en")
        if value not in (None, ""):
            return value
    return None


def _get_path(record: dict[str, Any], path: str) -> Any:
    value: Any = record
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _first_subdivision_name(record: dict[str, Any]) -> Any:
    subdivisions = record.get("subdivisions")
    if isinstance(subdivisions, list) and subdivisions:
        first = subdivisions[0]
        if isinstance(first, dict):
            return first.get("name") or first.get("iso_code") or _get_path(first, "names.en")
    return _first_value(record, "region", "region_name", "subdivision")


def _deep_merge(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = dict(left)
    for key, value in right.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _is_valid_ip(value: str) -> bool:
    try:
        ip_address(value)
        return True
    except ValueError:
        return False


def _is_public_ip(value: str) -> bool:
    try:
        parsed = ip_address(value)
    except ValueError:
        return False
    return not (
        parsed.is_private
        or parsed.is_loopback
        or parsed.is_link_local
        or parsed.is_multicast
        or parsed.is_reserved
        or parsed.is_unspecified
    )
