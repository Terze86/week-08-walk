"""Write-once file storage with SHA-256 integrity checks.

Original photographs, GeneMapper exports, EPG PDFs, CODIS files and issued
reports are kept exactly as received (WF-05.03, WF-11.05, WF-13.08, WF-17.08).
Content is addressed by its hash; the store refuses to overwrite an object, and
every read re-verifies the hash against the database record.
"""

import hashlib
import os
import uuid
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core import audit
from app.core.config import get_settings
from app.core.db import Base, UUIDPk, append_only
from app.core.errors import IntegrityFailure, NotFound


@append_only
class StoredFile(UUIDPk, Base):
    __tablename__ = "stored_file"

    sha256: Mapped[str] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    media_type: Mapped[str] = mapped_column(String(200))
    original_name: Mapped[str] = mapped_column(String(500))
    storage_key: Mapped[str] = mapped_column(String(200))
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class FileStore(Protocol):
    def exists(self, key: str) -> bool: ...
    def put(self, key: str, data: bytes) -> None: ...
    def get(self, key: str) -> bytes: ...


class LocalFileStore:
    """Development/test store. Files are created exclusively and made read-only."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError("Invalid storage key")
        return path

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def put(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()


class S3FileStore:
    """Production store: S3-compatible bucket with Object Lock (compliance mode)."""

    def __init__(self, bucket: str, endpoint_url: str | None, retention_days: int) -> None:
        import boto3

        self.bucket = bucket
        self.retention_days = retention_days
        self.client = boto3.client("s3", endpoint_url=endpoint_url)

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise
        return True

    def put(self, key: str, data: bytes) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            IfNoneMatch="*",
            ObjectLockMode="COMPLIANCE",
            ObjectLockRetainUntilDate=datetime.now(UTC) + timedelta(days=self.retention_days),
            ChecksumAlgorithm="SHA256",
        )

    def get(self, key: str) -> bytes:
        body: bytes = self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        return body


@lru_cache
def get_file_store() -> FileStore:
    settings = get_settings()
    if settings.file_store == "s3":
        return S3FileStore(
            settings.s3_bucket, settings.s3_endpoint_url, settings.s3_object_lock_days
        )
    return LocalFileStore(settings.file_store_path)


def _key_for(sha256: str) -> str:
    return f"sha256/{sha256[:2]}/{sha256}"


def store_file(
    session: Session,
    store: FileStore,
    *,
    data: bytes,
    original_name: str,
    media_type: str,
    actor_id: uuid.UUID,
) -> StoredFile:
    """Store bytes once (deduplicated by hash) and record this upload."""
    digest = hashlib.sha256(data).hexdigest()
    key = _key_for(digest)
    if store.exists(key):
        if hashlib.sha256(store.get(key)).hexdigest() != digest:
            raise IntegrityFailure(f"Stored object {key} does not match its hash")
    else:
        store.put(key, data)

    record = StoredFile(
        sha256=digest,
        size_bytes=len(data),
        media_type=media_type,
        original_name=original_name,
        storage_key=key,
        uploaded_by=actor_id,
    )
    session.add(record)
    session.flush()
    audit.record(
        session,
        actor_id=actor_id,
        action="file.uploaded",
        entity_type="stored_file",
        entity_id=record.id,
        after={"sha256": digest, "size": len(data), "name": original_name},
    )
    return record


def read_file(session: Session, store: FileStore, file_id: uuid.UUID) -> tuple[StoredFile, bytes]:
    record = session.get(StoredFile, file_id)
    if record is None:
        raise NotFound("File not found")
    data = store.get(record.storage_key)
    if hashlib.sha256(data).hexdigest() != record.sha256:
        raise IntegrityFailure(f"File {file_id} failed its integrity check")
    return record, data
