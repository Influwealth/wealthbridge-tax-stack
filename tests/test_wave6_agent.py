"""Wave 6: Caffeine Agent + Supabase hybrid architecture tests."""
import json
import time
import hmac
import hashlib
import base64
from unittest.mock import MagicMock, patch


# ─── Supabase auth ────────────────────────────────────────────────────────────

def _make_supabase_jwt(claims: dict, secret: str) -> str:
    """Generate a test Supabase-style JWT."""
    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = b64url(json.dumps(claims).encode())
    signing_input = f"{header}.{payload}".encode()
    sig = b64url(hmac.new(secret.encode(), signing_input, hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


def test_verify_supabase_jwt_valid():
    secret = "test_supabase_secret_key_32chars!!"
    claims = {"sub": "user-123", "email": "test@example.com", "exp": int(time.time()) + 3600}
    token = _make_supabase_jwt(claims, secret)

    with patch.dict("os.environ", {"SUPABASE_JWT_SECRET": secret}):
        import importlib
        import supabase.auth as sb_auth
        importlib.reload(sb_auth)
        result = sb_auth.verify_supabase_jwt(token)
    assert result is not None
    assert result["email"] == "test@example.com"


def test_verify_supabase_jwt_expired():
    secret = "test_supabase_secret_key_32chars!!"
    claims = {"sub": "user-123", "exp": int(time.time()) - 3600}  # already expired
    token = _make_supabase_jwt(claims, secret)

    with patch.dict("os.environ", {"SUPABASE_JWT_SECRET": secret}):
        from supabase.auth import verify_supabase_jwt
        result = verify_supabase_jwt(token)
    assert result is None


def test_verify_supabase_jwt_wrong_secret():
    claims = {"sub": "user-123", "exp": int(time.time()) + 3600}
    token = _make_supabase_jwt(claims, "correct_secret_32_chars_exactly!!")

    with patch.dict("os.environ", {"SUPABASE_JWT_SECRET": "wrong_secret_32_chars_exactly!!!"}):
        from supabase.auth import verify_supabase_jwt
        result = verify_supabase_jwt(token)
    assert result is None


def test_verify_supabase_jwt_not_configured():
    with patch.dict("os.environ", {"SUPABASE_JWT_SECRET": ""}):
        from supabase.auth import verify_supabase_jwt
        result = verify_supabase_jwt("some.fake.token")
    assert result is None


def test_extract_supabase_user_info():
    from supabase.auth import extract_supabase_user_info
    claims = {
        "sub": "uuid-abc",
        "email": "user@firm.com",
        "role": "authenticated",
        "app_metadata": {"provider": "email"},
        "user_metadata": {"name": "John"},
    }
    info = extract_supabase_user_info(claims)
    assert info["email"] == "user@firm.com"
    assert info["role"] == "authenticated"
    assert info["sub"] == "uuid-abc"


# ─── Supabase client ─────────────────────────────────────────────────────────

def test_is_supabase_configured_false():
    with patch.dict("os.environ", {"SUPABASE_URL": "", "SUPABASE_KEY": ""}):
        import importlib
        import supabase.client as sc
        importlib.reload(sc)
        assert sc.is_supabase_configured() is False


def test_get_supabase_client_not_configured():
    with patch.dict("os.environ", {"SUPABASE_URL": "", "SUPABASE_KEY": ""}):
        import importlib
        import supabase.client as sc
        importlib.reload(sc)
        client = sc.get_supabase_client()
    assert client is None


# ─── Storage abstraction ──────────────────────────────────────────────────────

def test_storage_backend_is_local_by_default():
    with patch.dict("os.environ", {"SUPABASE_URL": "", "SUPABASE_KEY": ""}):
        import importlib
        import supabase.client as sc
        importlib.reload(sc)
        import supabase.storage as ss
        importlib.reload(ss)
        backend = ss.get_storage_backend()
    assert isinstance(backend, ss.LocalStorageBackend)


def test_local_backend_store_retrieve(tmp_path, monkeypatch):
    monkeypatch.setattr("documents.vault.VAULT_DIR", tmp_path)
    from supabase.storage import LocalStorageBackend
    backend = LocalStorageBackend()
    content = b"test document wave6"
    meta = backend.store(1, "1120", "json", content)
    assert meta["size_bytes"] == len(content)
    retrieved = backend.retrieve(1, "1120", "json")
    assert retrieved == content


def test_local_backend_delete(tmp_path, monkeypatch):
    monkeypatch.setattr("documents.vault.VAULT_DIR", tmp_path)
    from supabase.storage import LocalStorageBackend
    backend = LocalStorageBackend()
    backend.store(2, "1065", "pdf", b"delete_me")
    deleted = backend.delete(2, "1065", "pdf")
    assert deleted is True
    assert backend.retrieve(2, "1065", "pdf") is None


def test_local_backend_validate(tmp_path, monkeypatch):
    monkeypatch.setattr("documents.vault.VAULT_DIR", tmp_path)
    from supabase.storage import LocalStorageBackend
    backend = LocalStorageBackend()
    backend.store(3, "941", "xml", b"valid_content")
    result = backend.validate(3, "941", "xml")
    assert result["valid"] is True


def test_local_backend_validate_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("documents.vault.VAULT_DIR", tmp_path)
    from supabase.storage import LocalStorageBackend
    backend = LocalStorageBackend()
    result = backend.validate(999, "1120", "pdf")
    assert result["valid"] is False


# ─── RLS helpers ─────────────────────────────────────────────────────────────

def test_enable_rls():
    from supabase.rls_helpers import enable_rls
    sql = enable_rls("tax_records")
    assert "ALTER TABLE tax_records ENABLE ROW LEVEL SECURITY" in sql


def test_owner_only_policy():
    from supabase.rls_helpers import owner_only_policy
    sql = owner_only_policy("tax_records")
    assert "CREATE POLICY" in sql
    assert "tax_records" in sql
    assert "auth.uid()" in sql


def test_admin_bypass_policy():
    from supabase.rls_helpers import admin_bypass_policy
    sql = admin_bypass_policy("rd_projects")
    assert "service_role" in sql
    assert "true" in sql


def test_generate_wealthbridge_rls():
    from supabase.rls_helpers import generate_wealthbridge_rls
    sql = generate_wealthbridge_rls()
    assert "tax_records" in sql
    assert "rd_projects" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql


# ─── Caffeine Agent ───────────────────────────────────────────────────────────

def test_agent_tools_schema():
    from caffeine_agent.tools import TOOL_SCHEMAS
    assert len(TOOL_SCHEMAS) >= 5
    names = {t["name"] for t in TOOL_SCHEMAS}
    assert "get_tax_record" in names
    assert "calculate_tax" in names
    assert "get_rd_credit_summary" in names


def test_agent_unavailable_without_key():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}):
        from caffeine_agent.agent import CaffeineAgent
        agent = CaffeineAgent(api_key="")
        result = agent.run([{"role": "user", "content": "Hello"}])
    assert result["status"] == "UNAVAILABLE"
    assert result["tool_calls_made"] == []


def test_agent_is_available_false_without_key():
    from caffeine_agent.agent import CaffeineAgent
    agent = CaffeineAgent(api_key="")
    assert agent.is_available() is False


def test_agent_run_mocked():
    """Test agent run with mocked Anthropic client."""
    from caffeine_agent.agent import CaffeineAgent

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.model = "claude-sonnet-4-6"
    mock_response.stop_reason = "end_turn"

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "The tax due for record 1 is $21,000."

    mock_response.content = [text_block]
    mock_client.messages.create.return_value = mock_response

    agent = CaffeineAgent(api_key="sk-test-key")
    agent._client = mock_client

    result = agent.run([{"role": "user", "content": "What is tax due for record 1?"}])
    assert result["status"] == "OK"
    assert "21,000" in result["response"]
    assert result["tool_calls_made"] == []


def test_agent_run_with_tool_call_mocked():
    from caffeine_agent.agent import CaffeineAgent

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.model = "claude-sonnet-4-6"
    mock_response.stop_reason = "tool_use"

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "get_tax_record"
    tool_block.input = {"record_id": 1}
    tool_block.id = "tool_abc123"

    mock_response.content = [tool_block]
    mock_client.messages.create.return_value = mock_response

    agent = CaffeineAgent(api_key="sk-test-key")
    agent._client = mock_client

    result = agent.run([{"role": "user", "content": "Get record 1"}])
    assert result["stop_reason"] == "tool_use"
    assert len(result["tool_calls_made"]) == 1
    assert result["tool_calls_made"][0]["name"] == "get_tax_record"


# ─── Agent API endpoints ──────────────────────────────────────────────────────

def test_api_agent_status(client, auth_headers):
    r = client.get("/agent/status", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "available" in data
    assert "model" in data
    assert data["tool_count"] >= 5


def test_api_agent_tools(client, auth_headers):
    r = client.get("/agent/tools", headers=auth_headers)
    assert r.status_code == 200
    tools = r.json()
    assert len(tools) >= 5
    names = {t["name"] for t in tools}
    assert "calculate_tax" in names


def test_api_agent_chat_unavailable(client, auth_headers):
    """Without ANTHROPIC_API_KEY the agent returns UNAVAILABLE, not an error."""
    r = client.post(
        "/agent/chat",
        json={"messages": [{"role": "user", "content": "What is my tax due?"}]},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "UNAVAILABLE"


def test_api_agent_chat_mocked(client, auth_headers):
    """Test agent chat with mocked CaffeineAgent."""
    mock_result = {
        "response": "Your tax due is $21,000 based on IRC §11.",
        "tool_calls_made": [],
        "model": "claude-sonnet-4-6",
        "status": "OK",
    }
    with patch("app.routers.agent._agent.run", return_value=mock_result):
        r = client.post(
            "/agent/chat",
            json={"messages": [{"role": "user", "content": "What is my tax?"}]},
            headers=auth_headers,
        )
    assert r.status_code == 200
    assert "21,000" in r.json()["response"]


def test_api_agent_chat_requires_auth(client):
    r = client.post(
        "/agent/chat",
        json={"messages": [{"role": "user", "content": "Hello"}]},
    )
    assert r.status_code == 401
