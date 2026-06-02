"""
Storage abstraction layer.

Provides a unified interface for document storage that can be backed by:
  - LocalStorageBackend: wraps documents/vault.py (default, no deps)
  - SupabaseStorageBackend: stores via Supabase Storage API

Selection is automatic:
  - If SUPABASE_URL + SUPABASE_KEY are set → SupabaseStorageBackend
  - Otherwise → LocalStorageBackend

Usage:
    from supabase.storage import get_storage_backend
    backend = get_storage_backend()
    meta = backend.store(record_id, doc_type, fmt, content)
    content = backend.retrieve(record_id, doc_type, fmt)
"""
import os
from typing import Optional, Protocol, runtime_checkable
from tax_capsule.utils.logger import get_logger

logger = get_logger("Storage")


@runtime_checkable
class StorageBackend(Protocol):
    def store(self, record_id: int, doc_type: str, fmt: str, content: bytes) -> dict: ...
    def retrieve(self, record_id: int, doc_type: str, fmt: str) -> Optional[bytes]: ...
    def delete(self, record_id: int, doc_type: str, fmt: str) -> bool: ...
    def list_documents(self, record_id: int) -> list[dict]: ...
    def validate(self, record_id: int, doc_type: str, fmt: str) -> dict: ...


class LocalStorageBackend:
    """Wraps documents/vault.py functions."""

    def store(self, record_id: int, doc_type: str, fmt: str, content: bytes) -> dict:
        from documents.vault import store_document
        return store_document(record_id, doc_type, fmt, content)

    def retrieve(self, record_id: int, doc_type: str, fmt: str) -> Optional[bytes]:
        from documents.vault import retrieve_document
        return retrieve_document(record_id, doc_type, fmt)

    def delete(self, record_id: int, doc_type: str, fmt: str) -> bool:
        from documents.vault import delete_document
        return delete_document(record_id, doc_type, fmt)

    def list_documents(self, record_id: int) -> list[dict]:
        from documents.vault import list_documents
        return list_documents(record_id)

    def validate(self, record_id: int, doc_type: str, fmt: str) -> dict:
        from documents.vault import validate_document
        return validate_document(record_id, doc_type, fmt)


class SupabaseStorageBackend:
    """
    Stores documents in Supabase Storage.

    Bucket name: SUPABASE_BUCKET (default: "tax-documents")
    Path pattern: {record_id}/{doc_type}.{fmt}
    """

    BUCKET = os.getenv("SUPABASE_BUCKET", "tax-documents")

    def __init__(self):
        from supabase.client import get_supabase_client
        self._client = get_supabase_client()
        if not self._client:
            raise RuntimeError("Supabase client not available")

    def _path(self, record_id: int, doc_type: str, fmt: str) -> str:
        return f"{record_id}/{doc_type}.{fmt}"

    def store(self, record_id: int, doc_type: str, fmt: str, content: bytes) -> dict:
        import hashlib
        path = self._path(record_id, doc_type, fmt)
        self._client.storage().from_(self.BUCKET).upload(path, content)
        return {
            "record_id": record_id,
            "doc_type": doc_type,
            "format": fmt,
            "size_bytes": len(content),
            "checksum_sha256": hashlib.sha256(content).hexdigest(),
            "backend": "supabase",
            "path": path,
        }

    def retrieve(self, record_id: int, doc_type: str, fmt: str) -> Optional[bytes]:
        try:
            path = self._path(record_id, doc_type, fmt)
            return self._client.storage().from_(self.BUCKET).download(path)
        except Exception as e:
            logger.warning(f"Supabase retrieve failed: {e}")
            return None

    def delete(self, record_id: int, doc_type: str, fmt: str) -> bool:
        try:
            path = self._path(record_id, doc_type, fmt)
            self._client.storage().from_(self.BUCKET).remove([path])
            return True
        except Exception as e:
            logger.warning(f"Supabase delete failed: {e}")
            return False

    def list_documents(self, record_id: int) -> list[dict]:
        try:
            result = (
                self._client.table("tax_documents")
                .select("*")
                .eq("record_id", record_id)
                .execute()
            )
            return result.get("data", [])
        except Exception as e:
            logger.warning(f"Supabase list failed: {e}")
            return []

    def validate(self, record_id: int, doc_type: str, fmt: str) -> dict:
        content = self.retrieve(record_id, doc_type, fmt)
        if content is None:
            return {"valid": False, "reason": "Document not found in Supabase Storage"}
        import hashlib
        return {"valid": True, "size_bytes": len(content), "checksum_sha256": hashlib.sha256(content).hexdigest()}


def get_storage_backend() -> StorageBackend:
    """Return the appropriate storage backend based on environment config."""
    from supabase.client import is_supabase_configured
    if is_supabase_configured():
        try:
            backend = SupabaseStorageBackend()
            logger.info("Using Supabase storage backend")
            return backend
        except Exception as e:
            logger.warning(f"Supabase storage unavailable ({e}), falling back to local")
    return LocalStorageBackend()
