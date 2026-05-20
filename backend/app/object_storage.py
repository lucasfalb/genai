import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import quote, urlparse

import httpx

from app.config import settings


@dataclass(frozen=True)
class StoredObject:
    bucket: str
    key: str
    etag: str | None = None


class ObjectStorageError(RuntimeError):
    pass


class S3ObjectStorage:
    def __init__(
        self,
        *,
        endpoint_url: str,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str,
        region: str,
        public: bool = False,
    ) -> None:
        self.endpoint_url = endpoint_url.rstrip("/")
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.bucket_name = bucket_name
        self.region = region
        self.public = public
        self._policy_applied = False
        parsed = urlparse(self.endpoint_url)
        self._host = parsed.netloc

    async def put_object(
        self,
        *,
        key: str,
        body: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> StoredObject:
        await self._ensure_bucket()
        response = await self._request(
            "PUT",
            f"/{self.bucket_name}/{key}",
            body=body,
            content_type=content_type,
            metadata=metadata,
        )
        if response.status_code not in (200, 201):
            raise ObjectStorageError(f"Object upload failed with status {response.status_code}")
        return StoredObject(bucket=self.bucket_name, key=key, etag=response.headers.get("etag"))

    def presign_url(
        self,
        *,
        bucket: str,
        key: str,
        expires: int = 900,
        method: str = "GET",
        response_content_type: str | None = None,
        response_content_disposition: str | None = None,
    ) -> str:
        safe_path = "/" + "/".join(
            quote(part, safe="") for part in f"{bucket}/{key}".strip("/").split("/")
        )
        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        credential_scope = f"{date_stamp}/{self.region}/s3/aws4_request"
        credential = f"{self.access_key_id}/{credential_scope}"

        query_params: dict[str, str] = {
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-Credential": credential,
            "X-Amz-Date": amz_date,
            "X-Amz-Expires": str(expires),
            "X-Amz-SignedHeaders": "host",
        }
        if response_content_type:
            query_params["response-content-type"] = response_content_type
        if response_content_disposition:
            query_params["response-content-disposition"] = response_content_disposition

        canonical_query = "&".join(
            f"{quote(k, safe='-_.~')}={quote(v, safe='-_.~')}"
            for k, v in sorted(query_params.items())
        )
        canonical_headers = f"host:{self._host}\n"
        canonical_request = "\n".join(
            [
                method,
                safe_path,
                canonical_query,
                canonical_headers,
                "host",
                "UNSIGNED-PAYLOAD",
            ]
        )
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                amz_date,
                credential_scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            ]
        )
        signature = hmac.new(
            self._signing_key(date_stamp),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"{self.endpoint_url}{safe_path}?{canonical_query}&X-Amz-Signature={signature}"

    async def get_object(self, *, bucket: str, key: str) -> bytes:
        response = await self._request("GET", f"/{bucket}/{key}", body=b"")
        if response.status_code != 200:
            raise ObjectStorageError(f"Object download failed with status {response.status_code}")
        return response.content

    async def delete_object(self, *, bucket: str, key: str) -> None:
        response = await self._request("DELETE", f"/{bucket}/{key}", body=b"")
        if response.status_code not in (200, 202, 204, 404):
            raise ObjectStorageError(f"Object delete failed with status {response.status_code}")

    async def _ensure_bucket(self) -> None:
        head = await self._request("HEAD", f"/{self.bucket_name}", body=b"")
        if head.status_code not in (200, 204):
            if head.status_code != 404:
                raise ObjectStorageError(f"Bucket check failed with status {head.status_code}")
            create = await self._request("PUT", f"/{self.bucket_name}", body=b"")
            if create.status_code not in (200, 201):
                raise ObjectStorageError(f"Bucket create failed with status {create.status_code}")
        if self.public and not self._policy_applied:
            await self._set_public_read_policy()

    async def _set_public_read_policy(self) -> None:
        import json
        policy = json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"],
            }],
        })
        body = policy.encode("utf-8")
        response = await self._request(
            "PUT",
            f"/{self.bucket_name}",
            body=body,
            content_type="application/json",
            query_string="policy=",
        )
        if response.status_code not in (200, 201, 204):
            raise ObjectStorageError(f"Set bucket policy failed with status {response.status_code}")
        self._policy_applied = True

    async def _request(
        self,
        method: str,
        path: str,
        *,
        body: bytes,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
        query_string: str = "",
    ) -> httpx.Response:
        safe_path = "/" + "/".join(quote(part, safe="") for part in path.strip("/").split("/"))
        url = f"{self.endpoint_url}{safe_path}"
        if query_string:
            url = f"{url}?{query_string}"
        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        payload_hash = hashlib.sha256(body).hexdigest()
        headers = {
            "host": self._host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
        }
        if content_type:
            headers["content-type"] = content_type
        if metadata:
            for mk, mv in metadata.items():
                headers[f"x-amz-meta-{mk.lower()}"] = quote(str(mv), safe="-_.~")

        signed_headers = ";".join(sorted(headers))
        canonical_headers = "".join(f"{name}:{headers[name]}\n" for name in sorted(headers))
        canonical_request = "\n".join(
            [method, safe_path, query_string, canonical_headers, signed_headers, payload_hash]
        )
        credential_scope = f"{date_stamp}/{self.region}/s3/aws4_request"
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                amz_date,
                credential_scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            ]
        )
        signature = hmac.new(
            self._signing_key(date_stamp),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        headers["authorization"] = (
            "AWS4-HMAC-SHA256 "
            f"Credential={self.access_key_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            return await client.request(method, url, content=body, headers=headers)

    def _signing_key(self, date_stamp: str) -> bytes:
        key_date = hmac.new(
            f"AWS4{self.secret_access_key}".encode("utf-8"),
            date_stamp.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        key_region = hmac.new(key_date, self.region.encode("utf-8"), hashlib.sha256).digest()
        key_service = hmac.new(key_region, b"s3", hashlib.sha256).digest()
        return hmac.new(key_service, b"aws4_request", hashlib.sha256).digest()


object_storage = S3ObjectStorage(
    endpoint_url=settings.s3_endpoint_url,
    access_key_id=settings.s3_access_key_id,
    secret_access_key=settings.s3_secret_access_key,
    bucket_name=settings.s3_bucket_name,
    region=settings.s3_region,
)

public_object_storage = S3ObjectStorage(
    endpoint_url=settings.s3_endpoint_url,
    access_key_id=settings.s3_access_key_id,
    secret_access_key=settings.s3_secret_access_key,
    bucket_name=settings.s3_public_bucket_name,
    region=settings.s3_region,
    public=True,
)
