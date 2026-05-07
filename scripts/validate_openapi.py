import argparse
import importlib
import sys
from pathlib import Path
from typing import Any


PUBLIC_ENDPOINTS = {
    ("GET", "/healthz"),
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/activation/request"),
    ("POST", "/api/v1/auth/activation/confirm"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/refresh"),
}


def load_openapi(repo_root: Path) -> dict[str, Any]:
    backend_dir = repo_root / "backend"
    sys.path.insert(0, str(backend_dir))
    module = importlib.import_module("app.main")
    return module.app.openapi()


def validate_openapi(schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    paths = schema.get("paths", {})
    if not paths:
        return ["OpenAPI schema has no paths"]

    operation_ids: set[str] = set()
    for path, path_item in sorted(paths.items()):
        for method, operation in sorted(path_item.items()):
            if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue

            location = f"{method.upper()} {path}"
            tags = operation.get("tags") or []
            if not tags:
                errors.append(f"{location}: missing tags")

            summary = (operation.get("summary") or "").strip()
            if len(summary) < 8:
                errors.append(f"{location}: summary must be explicit")

            description = (operation.get("description") or "").strip()
            if len(description) < 20:
                errors.append(f"{location}: description must explain the contract")

            operation_id = operation.get("operationId")
            if not operation_id:
                errors.append(f"{location}: missing operationId")
            elif operation_id in operation_ids:
                errors.append(f"{location}: duplicate operationId {operation_id}")
            else:
                operation_ids.add(operation_id)

            responses = operation.get("responses") or {}
            if "200" not in responses and "201" not in responses and "204" not in responses:
                errors.append(f"{location}: missing success response")

            if (method.upper(), path) not in PUBLIC_ENDPOINTS and not operation.get("security"):
                errors.append(f"{location}: protected endpoint must declare OpenAPI security")

            if any(param.get("name") == "X-Tenant-ID" for param in operation.get("parameters", [])):
                header = next(param for param in operation["parameters"] if param.get("name") == "X-Tenant-ID")
                if not header.get("required"):
                    errors.append(f"{location}: X-Tenant-ID must be required when present")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate FastAPI OpenAPI endpoint documentation.")
    parser.add_argument("--root", default=".", help="Repository root. Defaults to current directory.")
    args = parser.parse_args()

    schema = load_openapi(Path(args.root).resolve())
    errors = validate_openapi(schema)
    if errors:
        print("ERROR OpenAPI validation failed")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("OK OpenAPI endpoint documentation is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
