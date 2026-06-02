"""Wave 4: Cache layer, rate limiting, and background task tests."""
import time

from app.cache import (
    cache_set, cache_get, cache_delete, cache_clear_prefix,
    cached, is_redis_available,
)
from app.middleware.rate_limit import _local_buckets


# ─── Cache layer (in-process fallback) ───────────────────────────────────────


def test_cache_set_and_get():
    cache_set("test:key1", {"value": 42})
    result = cache_get("test:key1")
    assert result == {"value": 42}


def test_cache_get_missing_returns_none():
    assert cache_get("test:does_not_exist") is None


def test_cache_delete():
    cache_set("test:del", "to_delete")
    cache_delete("test:del")
    assert cache_get("test:del") is None


def test_cache_delete_nonexistent_no_error():
    cache_delete("test:ghost")  # should not raise


def test_cache_set_overwrites():
    cache_set("test:overwrite", "first")
    cache_set("test:overwrite", "second")
    assert cache_get("test:overwrite") == "second"


def test_cache_stores_list():
    cache_set("test:list", [1, 2, 3])
    assert cache_get("test:list") == [1, 2, 3]


def test_cache_stores_nested_dict():
    data = {"a": {"b": {"c": 99}}}
    cache_set("test:nested", data)
    assert cache_get("test:nested") == data


def test_cache_clear_prefix():
    cache_set("record:1:detail", {"id": 1})
    cache_set("record:1:summary", {"id": 1})
    cache_set("record:2:detail", {"id": 2})
    cache_set("other:key", "keep_me")

    deleted = cache_clear_prefix("record:1:")
    assert deleted == 2
    assert cache_get("record:1:detail") is None
    assert cache_get("record:1:summary") is None
    assert cache_get("record:2:detail") == {"id": 2}
    assert cache_get("other:key") == "keep_me"


def test_cache_clear_prefix_no_matches():
    deleted = cache_clear_prefix("nonexistent:")
    assert deleted == 0


# ─── @cached decorator ────────────────────────────────────────────────────────

def test_cached_decorator_caches_result():
    call_count = 0

    @cached("deco_test", ttl=60)
    def expensive(x):
        nonlocal call_count
        call_count += 1
        return x * 2

    result1 = expensive(5)
    result2 = expensive(5)
    assert result1 == 10
    assert result2 == 10
    assert call_count == 1  # only called once


def test_cached_decorator_different_args():
    @cached("deco_args", ttl=60)
    def double(x):
        return x * 2

    assert double(3) == 6
    assert double(4) == 8


def test_cached_decorator_kwargs():
    call_count = 0

    @cached("deco_kw", ttl=60)
    def fn(a, b=10):
        nonlocal call_count
        call_count += 1
        return a + b

    fn(1, b=2)
    fn(1, b=2)
    assert call_count == 1


# ─── Redis availability check ─────────────────────────────────────────────────

def test_is_redis_available_without_redis():
    # No REDIS_URL set in test environment → should return False
    assert is_redis_available() is False


# ─── Rate limiting middleware (via API client) ────────────────────────────────

def test_rate_limit_health_exempt(client):
    """Health endpoint is exempt from rate limiting."""
    for _ in range(5):
        r = client.get("/health")
        assert r.status_code == 200


def test_rate_limit_allows_normal_traffic(client, auth_headers):
    """Normal traffic under the limit should all succeed."""
    for _ in range(3):
        r = client.get("/tax/records/", headers=auth_headers)
        assert r.status_code == 200


def test_rate_limit_429_when_exceeded(client, auth_headers):
    """Hammer the endpoint beyond per-minute limit to trigger 429."""
    from app.middleware.rate_limit import RATE_LIMIT_PER_MINUTE

    ip = "testclient"
    # Pre-fill bucket to simulate limit already reached
    _local_buckets[ip] = (time.time(), RATE_LIMIT_PER_MINUTE)

    r = client.get("/tax/records/", headers=auth_headers)
    assert r.status_code == 429
    assert "Rate limit exceeded" in r.json()["detail"]
    assert r.headers.get("Retry-After") == "60"


def test_rate_limit_resets_after_window(client, auth_headers):
    """After the 1-minute window rolls over, counter should reset."""
    from app.middleware.rate_limit import RATE_LIMIT_PER_MINUTE

    ip = "testclient"
    # Set window start to 2 minutes ago (expired)
    _local_buckets[ip] = (time.time() - 120, RATE_LIMIT_PER_MINUTE)

    r = client.get("/tax/records/", headers=auth_headers)
    assert r.status_code == 200


# ─── Background task: invalidate_record_cache ─────────────────────────────────

def test_invalidate_record_cache_clears_keys():
    from app.tasks import invalidate_record_cache

    cache_set("record:42:detail", {"id": 42})
    cache_set("record:42:summary", {"id": 42})
    cache_set("record:43:detail", {"id": 43})

    invalidate_record_cache(42)

    assert cache_get("record:42:detail") is None
    assert cache_get("record:42:summary") is None
    assert cache_get("record:43:detail") == {"id": 43}  # unaffected


def test_invalidate_record_cache_no_keys_no_error():
    from app.tasks import invalidate_record_cache
    invalidate_record_cache(9999)  # no keys exist, should not raise


# ─── Cache integration via API ────────────────────────────────────────────────

def test_get_record_served_from_cache(client, auth_headers):
    """Second GET on same record should return same data (cache hit path)."""
    r = client.post(
        "/tax/records/",
        json={"entity_name": "Cache Corp", "tax_year": 2024, "income": "100000",
              "entity_type": "corporation"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    record_id = r.json()["id"]

    r1 = client.get(f"/tax/records/{record_id}", headers=auth_headers)
    r2 = client.get(f"/tax/records/{record_id}", headers=auth_headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]


def test_update_evicts_cache(client, auth_headers):
    """After PATCH, the stale cache entry should be replaced."""
    r = client.post(
        "/tax/records/",
        json={"entity_name": "Evict Corp", "tax_year": 2024, "income": "100000",
              "entity_type": "corporation"},
        headers=auth_headers,
    )
    record_id = r.json()["id"]

    client.get(f"/tax/records/{record_id}", headers=auth_headers)  # prime cache

    r_patch = client.patch(
        f"/tax/records/{record_id}",
        json={"entity_name": "Evict Corp Updated"},
        headers=auth_headers,
    )
    assert r_patch.status_code == 200

    r_get = client.get(f"/tax/records/{record_id}", headers=auth_headers)
    assert r_get.json()["entity_name"] == "Evict Corp Updated"


def test_delete_evicts_cache(client, auth_headers):
    """After DELETE, GETting the record should return 404."""
    r = client.post(
        "/tax/records/",
        json={"entity_name": "Delete Corp", "tax_year": 2024, "income": "50000",
              "entity_type": "corporation"},
        headers=auth_headers,
    )
    record_id = r.json()["id"]

    client.get(f"/tax/records/{record_id}", headers=auth_headers)  # prime cache
    client.delete(f"/tax/records/{record_id}", headers=auth_headers)

    r_get = client.get(f"/tax/records/{record_id}", headers=auth_headers)
    assert r_get.status_code == 404
