"""
Supabase client wrapper.

Uses the official supabase-py SDK when installed; falls back to raw requests
for environments where the SDK is not available.

Config via env vars:
  SUPABASE_URL   e.g. https://xxxx.supabase.co
  SUPABASE_KEY   anon/service-role key
"""
import os
from typing import Optional
from tax_capsule.utils.logger import get_logger

logger = get_logger("SupabaseClient")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


def is_supabase_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def get_supabase_client():
    """
    Return a Supabase client instance, or None if not configured.

    Tries supabase-py SDK first; falls back to a minimal requests-based shim.
    """
    if not is_supabase_configured():
        return None

    try:
        from supabase import create_client  # type: ignore
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info(f"Supabase client initialized: {SUPABASE_URL}")
        return client
    except ImportError:
        logger.info("supabase-py SDK not installed — using requests shim")
        return _SupabaseRequestsShim(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logger.warning(f"Supabase client init failed: {e}")
        return None


class _SupabaseRequestsShim:
    """Minimal Supabase REST client for environments without supabase-py."""

    def __init__(self, url: str, key: str):
        self.url = url.rstrip("/")
        self.key = key
        self._headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def _rest_url(self, path: str) -> str:
        return f"{self.url}/rest/v1/{path.lstrip('/')}"

    def table(self, name: str) -> "_TableQuery":
        return _TableQuery(name, self._rest_url(name), self._headers)

    def storage(self) -> "_StorageClient":
        return _StorageClient(self.url, self._headers)


class _TableQuery:
    def __init__(self, name: str, url: str, headers: dict):
        self.name = name
        self._url = url
        self._headers = headers
        self._filters: list[str] = []
        self._select = "*"

    def select(self, columns: str = "*"):
        self._select = columns
        return self

    def eq(self, column: str, value) -> "_TableQuery":
        self._filters.append(f"{column}=eq.{value}")
        return self

    def execute(self) -> dict:
        import requests
        params = {"select": self._select}
        for f in self._filters:
            k, v = f.split("=", 1)
            params[k] = v
        r = requests.get(self._url, headers=self._headers, params=params, timeout=10)
        r.raise_for_status()
        return {"data": r.json(), "error": None}

    def insert(self, record: dict) -> "_TableQuery":
        import requests
        r = requests.post(self._url, headers=self._headers, json=record, timeout=10)
        r.raise_for_status()
        return {"data": r.json(), "error": None}


class _StorageClient:
    def __init__(self, base_url: str, headers: dict):
        self._base_url = base_url.rstrip("/")
        self._headers = headers

    def from_(self, bucket: str) -> "_BucketClient":
        return _BucketClient(self._base_url, bucket, self._headers)


class _BucketClient:
    def __init__(self, base_url: str, bucket: str, headers: dict):
        self._url = f"{base_url}/storage/v1/object/{bucket}"
        self._headers = headers

    def upload(self, path: str, content: bytes, file_options: dict | None = None) -> dict:
        import requests
        headers = {**self._headers, "Content-Type": "application/octet-stream"}
        r = requests.post(f"{self._url}/{path}", headers=headers, data=content, timeout=30)
        r.raise_for_status()
        return {"data": {"path": path}, "error": None}

    def download(self, path: str) -> bytes:
        import requests
        r = requests.get(f"{self._url}/{path}", headers=self._headers, timeout=30)
        r.raise_for_status()
        return r.content

    def remove(self, paths: list[str]) -> dict:
        import requests
        r = requests.delete(
            f"{self._url}",
            headers={**self._headers, "Content-Type": "application/json"},
            json={"prefixes": paths},
            timeout=10,
        )
        r.raise_for_status()
        return {"data": r.json(), "error": None}
