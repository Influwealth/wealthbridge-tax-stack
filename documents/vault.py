"""
Document vault — store, retrieve, list, and delete tax documents.
Currently uses local filesystem storage.
Interface is designed to be swapped for S3 or Supabase Storage with minimal changes:
  replace _store_local / _retrieve_local with provider-specific implementations.
"""
import os
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from tax_capsule.utils.logger import get_logger

logger = get_logger("DocumentVault")

VAULT_DIR = Path(os.getenv("DOCUMENT_VAULT_DIR", "/tmp/wealthbridge_vault"))


def _ensure_vault() -> Path:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    return VAULT_DIR


def _doc_key(record_id: int, doc_type: str, fmt: str) -> str:
    """Generate a deterministic storage key."""
    return f"record_{record_id}_{doc_type}.{fmt}"


def store_document(
    record_id: int,
    doc_type: str,        # e.g. "1120", "1065", "schedule_c"
    fmt: str,             # "pdf" | "xml" | "json"
    content: bytes,
) -> dict:
    """Store a document and return its metadata."""
    vault = _ensure_vault()
    key = _doc_key(record_id, doc_type, fmt)
    path = vault / key
    path.write_bytes(content)

    checksum = hashlib.sha256(content).hexdigest()
    meta = {
        "key": key,
        "record_id": record_id,
        "doc_type": doc_type,
        "format": fmt,
        "size_bytes": len(content),
        "checksum_sha256": checksum,
        "stored_at": datetime.now(timezone.utc).isoformat(),
        "path": str(path),
    }

    # Write sidecar metadata file
    (vault / f"{key}.meta.json").write_text(json.dumps(meta))
    logger.info(f"Stored document: {key} ({len(content)} bytes, sha256={checksum[:8]}...)")
    return meta


def retrieve_document(record_id: int, doc_type: str, fmt: str) -> Optional[bytes]:
    """Return document bytes, or None if not found."""
    vault = _ensure_vault()
    path = vault / _doc_key(record_id, doc_type, fmt)
    if not path.exists():
        logger.warning(f"Document not found: {path.name}")
        return None
    return path.read_bytes()


def list_documents(record_id: Optional[int] = None) -> list[dict]:
    """List stored documents, optionally filtered by record_id."""
    vault = _ensure_vault()
    docs = []
    for meta_file in vault.glob("*.meta.json"):
        try:
            meta = json.loads(meta_file.read_text())
            if record_id is None or meta.get("record_id") == record_id:
                docs.append(meta)
        except Exception:
            pass
    return sorted(docs, key=lambda d: d.get("stored_at", ""), reverse=True)


def delete_document(record_id: int, doc_type: str, fmt: str) -> bool:
    """Delete a stored document. Returns True if deleted, False if not found."""
    vault = _ensure_vault()
    key = _doc_key(record_id, doc_type, fmt)
    path = vault / key
    meta_path = vault / f"{key}.meta.json"
    if not path.exists():
        return False
    path.unlink()
    if meta_path.exists():
        meta_path.unlink()
    logger.info(f"Deleted document: {key}")
    return True


def validate_document(record_id: int, doc_type: str, fmt: str) -> dict:
    """Validate a stored document by re-checking its SHA-256 checksum."""
    vault = _ensure_vault()
    key = _doc_key(record_id, doc_type, fmt)
    path = vault / key
    meta_path = vault / f"{key}.meta.json"

    if not path.exists():
        return {"valid": False, "error": "Document not found"}

    content = path.read_bytes()
    actual_checksum = hashlib.sha256(content).hexdigest()

    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        expected = meta.get("checksum_sha256", "")
        if actual_checksum != expected:
            return {
                "valid": False,
                "error": "Checksum mismatch — document may be corrupted",
                "expected": expected,
                "actual": actual_checksum,
            }

    return {"valid": True, "checksum_sha256": actual_checksum, "size_bytes": len(content)}
