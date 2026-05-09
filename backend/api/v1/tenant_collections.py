import json
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.cache import redis_client
from app.config import settings
from app.object_storage import ObjectStorageError, object_storage
from app.rbac import Permission
from app.responses import api_success
from app.schemas import (
    ApiResponse,
    CollectionCreateRequest,
    CollectionResponse,
    CollectionUpdateRequest,
    DocumentResponse,
    MessageResponse,
)
from app.workflow_audit import record_tenant_mutation
from database.connection import TenantContext
from database.repositories.collections import CollectionRecord, CollectionRepository
from database.repositories.documents import DocumentRecord, DocumentRepository
from dependencies.auth import get_connection, require_permission

router = APIRouter(prefix="/tenant/collections", tags=["tenant-collections"])

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
}
INDEXING_QUEUE_KEY = "rag:indexing_queue"


@router.get(
    "",
    response_model=ApiResponse[list[CollectionResponse]],
    summary="List collections",
    description="Lists all document collections for the selected tenant. Requires Bearer auth, X-Tenant-ID, and agent-instance management permission.",
)
async def list_collections(
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[list[CollectionResponse]]:
    await _set_tenant(connection, context)
    collections = await CollectionRepository(connection).list(tenant_id=context.tenant_id)
    return api_success([_collection_response(c) for c in collections])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[CollectionResponse],
    summary="Create collection",
    description="Creates a new document collection for the selected tenant with empty indexing status and records an audit entry.",
)
async def create_collection(
    payload: CollectionCreateRequest,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[CollectionResponse]:
    await _set_tenant(connection, context)
    collection = await CollectionRepository(connection).create(
        tenant_id=context.tenant_id,
        name=payload.name,
        description=payload.description,
    )
    await record_tenant_mutation(
        connection=connection,
        context=context,
        action="collection.created",
        resource="collections",
        resource_id=str(collection.id),
        snapshot=_collection_response(collection).model_dump(mode="json"),
        metadata=payload.model_dump(),
    )
    return api_success(_collection_response(collection), message="Collection created.")


@router.get(
    "/{collection_id}",
    response_model=ApiResponse[CollectionResponse],
    summary="Get collection",
    description="Returns details of a single document collection scoped to the selected tenant.",
)
async def get_collection(
    collection_id: UUID,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[CollectionResponse]:
    await _set_tenant(connection, context)
    collection = await CollectionRepository(connection).get(
        tenant_id=context.tenant_id, collection_id=collection_id
    )
    if collection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection not found")
    return api_success(_collection_response(collection))


@router.patch(
    "/{collection_id}",
    response_model=ApiResponse[CollectionResponse],
    summary="Update collection",
    description="Partially updates name or description of a document collection and records an audit entry.",
)
async def update_collection(
    collection_id: UUID,
    payload: CollectionUpdateRequest,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[CollectionResponse]:
    if not payload.model_fields_set:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No changes provided")
    await _set_tenant(connection, context)
    collection = await CollectionRepository(connection).update_metadata(
        tenant_id=context.tenant_id,
        collection_id=collection_id,
        **payload.model_dump(exclude_unset=True),
    )
    if collection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection not found")
    await record_tenant_mutation(
        connection=connection,
        context=context,
        action="collection.updated",
        resource="collections",
        resource_id=str(collection_id),
        snapshot=_collection_response(collection).model_dump(mode="json"),
        metadata=payload.model_dump(exclude_unset=True),
    )
    return api_success(_collection_response(collection), message="Collection updated.")


@router.delete(
    "/{collection_id}",
    response_model=ApiResponse[MessageResponse],
    summary="Delete collection",
    description="Deletes a document collection and all its documents. Returns 409 if any documents are indexed.",
)
async def delete_collection(
    collection_id: UUID,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[MessageResponse]:
    await _set_tenant(connection, context)
    repo = CollectionRepository(connection)
    collection = await repo.get(tenant_id=context.tenant_id, collection_id=collection_id)
    if collection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection not found")
    if collection.indexed_count > 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cannot delete collection with indexed documents")
    await record_tenant_mutation(
        connection=connection,
        context=context,
        action="collection.deleted",
        resource="collections",
        resource_id=str(collection_id),
        metadata={"collection_name": collection.name},
    )
    await repo.delete(tenant_id=context.tenant_id, collection_id=collection_id)
    message = "Collection deleted."
    return api_success(MessageResponse(message=message), message=message)


@router.post(
    "/{collection_id}/reindex",
    response_model=ApiResponse[CollectionResponse],
    summary="Reindex collection",
    description="Resets all documents in the collection to uploaded status and enqueues indexing jobs for the worker.",
)
async def reindex_collection(
    collection_id: UUID,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[CollectionResponse]:
    await _set_tenant(connection, context)
    collection_repo = CollectionRepository(connection)
    document_repo = DocumentRepository(connection)
    collection = await collection_repo.get(tenant_id=context.tenant_id, collection_id=collection_id)
    if collection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection not found")

    documents = await document_repo.reset_collection_for_reindex(
        tenant_id=context.tenant_id,
        collection_id=collection_id,
    )
    stats = await document_repo.recalc_collection_stats(
        tenant_id=context.tenant_id,
        collection_id=collection_id,
    )
    updated = await collection_repo.update_indexing_status(
        tenant_id=context.tenant_id,
        collection_id=collection_id,
        indexing_status="indexing" if documents else "empty",
        indexing_progress=0.0,
        document_count=stats["document_count"],
        indexed_count=stats["indexed_count"],
        failed_count=stats["failed_count"],
    )

    for document in documents:
        try:
            await redis_client.rpush(
                INDEXING_QUEUE_KEY,
                json.dumps(
                    {
                        "document_id": str(document.id),
                        "tenant_id": str(context.tenant_id),
                        "collection_id": str(collection_id),
                    }
                ),
            )
        except (RedisError, RuntimeError):
            pass

    await record_tenant_mutation(
        connection=connection,
        context=context,
        action="collection.reindex_requested",
        resource="collections",
        resource_id=str(collection_id),
        snapshot=_collection_response(updated or collection).model_dump(mode="json"),
        metadata={"document_count": len(documents)},
    )
    return api_success(
        _collection_response(updated or collection),
        message="Collection reindex queued.",
    )


@router.post(
    "/{collection_id}/documents",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[DocumentResponse],
    summary="Upload document to collection",
    description="Uploads a document file (PDF/DOCX/TXT/MD) up to the configured size limit, stores it in S3-compatible object storage, and enqueues an indexing job.",
)
async def upload_document(
    collection_id: UUID,
    file: UploadFile = File(...),
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[DocumentResponse]:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Unsupported content type: {file.content_type}",
        )
    payload = await file.read()
    if len(payload) > settings.upload_max_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds maximum size of {settings.upload_max_bytes} bytes",
        )
    if len(payload) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")

    await _set_tenant(connection, context)
    collection = await CollectionRepository(connection).get(
        tenant_id=context.tenant_id, collection_id=collection_id
    )
    if collection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection not found")

    document_id = uuid4()
    safe_filename = _safe_filename(file.filename)
    object_key = "/".join(
        [
            "tenants",
            str(context.tenant_id),
            "collections",
            str(collection_id),
            "documents",
            str(document_id),
            safe_filename,
        ]
    )
    try:
        stored_object = await object_storage.put_object(
            key=object_key,
            body=payload,
            content_type=file.content_type or "application/octet-stream",
        )
    except ObjectStorageError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Document storage is unavailable",
        ) from exc

    document_repo = DocumentRepository(connection)
    try:
        document = await document_repo.create(
            document_id=document_id,
            tenant_id=context.tenant_id,
            collection_id=collection_id,
            filename=safe_filename,
            source_type="upload",
            storage_bucket=stored_object.bucket,
            storage_key=stored_object.key,
            content_type=file.content_type,
            size_bytes=len(payload),
        )
    except Exception:
        await _delete_stored_object(stored_object.bucket, stored_object.key)
        raise

    stats = await document_repo.recalc_collection_stats(
        tenant_id=context.tenant_id, collection_id=collection_id
    )
    await CollectionRepository(connection).update_indexing_status(
        tenant_id=context.tenant_id,
        collection_id=collection_id,
        indexing_status="indexing",
        document_count=stats["document_count"],
        indexed_count=stats["indexed_count"],
        failed_count=stats["failed_count"],
    )

    await record_tenant_mutation(
        connection=connection,
        context=context,
        action="document.uploaded",
        resource="documents",
        resource_id=str(document.id),
        snapshot=_document_response(document).model_dump(mode="json"),
        metadata={"collection_id": str(collection_id), "filename": safe_filename, "size_bytes": len(payload)},
    )

    try:
        await redis_client.rpush(
            INDEXING_QUEUE_KEY,
            json.dumps(
                {
                    "document_id": str(document.id),
                    "tenant_id": str(context.tenant_id),
                    "collection_id": str(collection_id),
                }
            ),
        )
    except (RedisError, RuntimeError):
        pass

    return api_success(_document_response(document), message="Document uploaded.")


@router.get(
    "/{collection_id}/documents",
    response_model=ApiResponse[list[DocumentResponse]],
    summary="List documents in collection",
    description="Returns all documents for the given collection ordered by creation time desc.",
)
async def list_documents(
    collection_id: UUID,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[list[DocumentResponse]]:
    await _set_tenant(connection, context)
    collection = await CollectionRepository(connection).get(
        tenant_id=context.tenant_id, collection_id=collection_id
    )
    if collection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection not found")
    documents = await DocumentRepository(connection).list_by_collection(
        tenant_id=context.tenant_id, collection_id=collection_id
    )
    return api_success([_document_response(d) for d in documents])


@router.get(
    "/{collection_id}/documents/{document_id}",
    response_model=ApiResponse[DocumentResponse],
    summary="Get document",
    description="Returns details for a single document including indexing status and error message if any.",
)
async def get_document(
    collection_id: UUID,
    document_id: UUID,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[DocumentResponse]:
    await _set_tenant(connection, context)
    document = await DocumentRepository(connection).get(
        tenant_id=context.tenant_id, document_id=document_id
    )
    if document is None or document.collection_id != collection_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return api_success(_document_response(document))


@router.delete(
    "/{collection_id}/documents/{document_id}",
    response_model=ApiResponse[MessageResponse],
    summary="Delete document",
    description="Removes the document, its object-storage file, and recalculates collection stats. Indexed chunks in Qdrant are removed by the worker.",
)
async def delete_document(
    collection_id: UUID,
    document_id: UUID,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[MessageResponse]:
    await _set_tenant(connection, context)
    repo = DocumentRepository(connection)
    document = await repo.get(tenant_id=context.tenant_id, document_id=document_id)
    if document is None or document.collection_id != collection_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    if document.storage_bucket and document.storage_key:
        await _delete_stored_object(document.storage_bucket, document.storage_key)

    await repo.delete(tenant_id=context.tenant_id, document_id=document_id)
    stats = await repo.recalc_collection_stats(
        tenant_id=context.tenant_id, collection_id=collection_id
    )
    new_status = "empty" if stats["document_count"] == 0 else "indexing"
    await CollectionRepository(connection).update_indexing_status(
        tenant_id=context.tenant_id,
        collection_id=collection_id,
        indexing_status=new_status,
        document_count=stats["document_count"],
        indexed_count=stats["indexed_count"],
        failed_count=stats["failed_count"],
    )

    await record_tenant_mutation(
        connection=connection,
        context=context,
        action="document.deleted",
        resource="documents",
        resource_id=str(document_id),
        metadata={"collection_id": str(collection_id), "filename": document.filename},
    )

    try:
        await redis_client.rpush(
            INDEXING_QUEUE_KEY,
            json.dumps(
                {
                    "action": "delete",
                    "document_id": str(document_id),
                    "tenant_id": str(context.tenant_id),
                    "collection_id": str(collection_id),
                }
            ),
        )
    except (RedisError, RuntimeError):
        pass

    message = "Document deleted."
    return api_success(MessageResponse(message=message), message=message)


async def _set_tenant(connection: AsyncConnection, context: TenantContext) -> None:
    await connection.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(context.tenant_id)},
    )


def _document_response(record: DocumentRecord) -> DocumentResponse:
    return DocumentResponse(
        id=record.id,
        tenant_id=record.tenant_id,
        collection_id=record.collection_id,
        filename=record.filename,
        source_type=record.source_type,
        status=record.status,
        chunk_count=record.chunk_count,
        error_message=record.error_message,
        content_type=record.content_type,
        size_bytes=record.size_bytes,
        created_at=record.created_at,
        indexed_at=record.indexed_at,
    )


def _safe_filename(filename: str | None) -> str:
    raw = filename or "document"
    safe = raw.replace("\\", "/").split("/")[-1].strip()
    return safe or "document"


async def _delete_stored_object(bucket: str, key: str) -> None:
    try:
        await object_storage.delete_object(bucket=bucket, key=key)
    except ObjectStorageError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Document storage is unavailable",
        ) from exc


def _collection_response(record: CollectionRecord) -> CollectionResponse:
    return CollectionResponse(
        id=record.id,
        tenant_id=record.tenant_id,
        name=record.name,
        description=record.description,
        indexing_status=record.indexing_status,
        indexing_progress=record.indexing_progress,
        document_count=record.document_count,
        indexed_count=record.indexed_count,
        failed_count=record.failed_count,
        last_indexed_at=record.last_indexed_at,
        created_at=record.created_at,
    )
