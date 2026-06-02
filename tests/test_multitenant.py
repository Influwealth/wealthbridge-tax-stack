"""Wave 8: Multi-Tenant Architecture — firm/tenant management, audit logging, isolation tests."""
from app import models
from audit.logger import log_action, get_audit_trail


# ─── Audit logger — unit tests ────────────────────────────────────────────────

def test_audit_log_create(db_session, admin_user):
    entry = log_action(
        db=db_session,
        action="create",
        resource_type="tax_record",
        resource_id=42,
        user_id=admin_user.id,
        details={"entity": "Test Corp"},
    )
    assert entry.id is not None
    assert entry.action == "create"
    assert entry.resource_type == "tax_record"
    assert entry.resource_id == 42
    assert entry.user_id == admin_user.id
    assert "Test Corp" in (entry.details or "")


def test_audit_log_immutable_no_update(db_session, admin_user):
    """Verify the audit logger has no update method (append-only design)."""
    # Only log_action and get_audit_trail exist — no update function
    import audit.logger as al
    public_fns = [name for name in dir(al) if not name.startswith("_")]
    assert "log_action" in public_fns
    assert "get_audit_trail" in public_fns
    # There must be no update/delete functions
    assert "update_action" not in public_fns
    assert "delete_log" not in public_fns


def test_audit_log_query_by_resource(db_session, admin_user):
    log_action(db=db_session, action="read", resource_type="tax_record",
               resource_id=10, user_id=admin_user.id)
    log_action(db=db_session, action="delete", resource_type="rd_project",
               resource_id=5, user_id=admin_user.id)

    records = get_audit_trail(db_session, resource_type="tax_record")
    assert all(lg.resource_type == "tax_record" for lg in records)


def test_audit_log_query_by_user(db_session, admin_user, accountant_user):
    log_action(db=db_session, action="create", resource_type="tax_record",
               resource_id=1, user_id=admin_user.id)
    log_action(db=db_session, action="read", resource_type="tax_record",
               resource_id=2, user_id=accountant_user.id)

    admin_logs = get_audit_trail(db_session, user_id=admin_user.id)
    assert all(lg.user_id == admin_user.id for lg in admin_logs)


def test_audit_log_with_tenant(db_session, admin_user):
    # Create firm + tenant first
    firm = models.Firm(name="Test Firm", slug="test-firm")
    db_session.add(firm)
    db_session.flush()
    tenant = models.Tenant(firm_id=firm.id, name="Client A")
    db_session.add(tenant)
    db_session.flush()

    entry = log_action(
        db=db_session, action="create", resource_type="tax_record",
        resource_id=99, user_id=admin_user.id, tenant_id=tenant.id,
    )
    assert entry.tenant_id == tenant.id

    tenant_logs = get_audit_trail(db_session, tenant_id=tenant.id)
    assert len(tenant_logs) >= 1


# ─── Tenant middleware — unit tests ───────────────────────────────────────────

def test_tenant_middleware_parses_header():
    from app.middleware.tenant import TENANT_HEADER
    assert TENANT_HEADER == "X-Tenant-ID"


def test_tenant_middleware_get_tenant_id_dependency():
    """get_tenant_id is a FastAPI dependency that reads from request.state."""
    from app.middleware.tenant import get_tenant_id
    from unittest.mock import MagicMock
    request = MagicMock()
    request.state.tenant_id = 42
    assert get_tenant_id(request) == 42


def test_tenant_middleware_missing_returns_none():
    from app.middleware.tenant import get_tenant_id
    from unittest.mock import MagicMock
    request = MagicMock()
    del request.state.tenant_id  # attribute doesn't exist
    request.state = MagicMock(spec=[])  # no tenant_id attribute
    assert get_tenant_id(request) is None


# ─── Firm CRUD — API tests ────────────────────────────────────────────────────

def test_api_create_firm(client, auth_headers):
    r = client.post(
        "/admin/firms",
        json={"name": "Acme Tax Partners", "slug": "acme-tax", "plan": "pro"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["slug"] == "acme-tax"
    assert data["plan"] == "pro"
    assert data["is_active"] is True


def test_api_create_firm_duplicate_slug(client, auth_headers):
    client.post(
        "/admin/firms",
        json={"name": "First Firm", "slug": "unique-slug"},
        headers=auth_headers,
    )
    r = client.post(
        "/admin/firms",
        json={"name": "Second Firm", "slug": "unique-slug"},
        headers=auth_headers,
    )
    assert r.status_code == 409


def test_api_list_firms(client, auth_headers):
    client.post(
        "/admin/firms",
        json={"name": "List Firm A", "slug": "list-firm-a"},
        headers=auth_headers,
    )
    r = client.get("/admin/firms", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_api_create_firm_requires_admin(client, agent_headers):
    r = client.post(
        "/admin/firms",
        json={"name": "Blocked Firm", "slug": "blocked"},
        headers=agent_headers,
    )
    assert r.status_code == 403


def test_api_invalid_plan(client, auth_headers):
    r = client.post(
        "/admin/firms",
        json={"name": "Bad Plan", "slug": "bad-plan", "plan": "free"},
        headers=auth_headers,
    )
    assert r.status_code == 422


# ─── Tenant CRUD — API tests ──────────────────────────────────────────────────

def _create_firm(client, auth_headers, slug="test-tenant-firm"):
    r = client.post(
        "/admin/firms",
        json={"name": f"Firm {slug}", "slug": slug},
        headers=auth_headers,
    )
    assert r.status_code == 201
    return r.json()["id"]


def test_api_create_tenant(client, auth_headers):
    firm_id = _create_firm(client, auth_headers, "ct-firm")
    r = client.post(
        f"/admin/firms/{firm_id}/tenants",
        json={"name": "Client Alpha", "external_id": "crm-001"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Client Alpha"
    assert data["external_id"] == "crm-001"
    assert data["firm_id"] == firm_id


def test_api_list_tenants(client, auth_headers):
    firm_id = _create_firm(client, auth_headers, "lt-firm")
    client.post(f"/admin/firms/{firm_id}/tenants",
                json={"name": "Tenant X"}, headers=auth_headers)
    client.post(f"/admin/firms/{firm_id}/tenants",
                json={"name": "Tenant Y"}, headers=auth_headers)

    r = client.get(f"/admin/firms/{firm_id}/tenants", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 2


def test_api_deactivate_tenant(client, auth_headers):
    firm_id = _create_firm(client, auth_headers, "dt-firm")
    r = client.post(f"/admin/firms/{firm_id}/tenants",
                    json={"name": "To Deactivate"}, headers=auth_headers)
    tenant_id = r.json()["id"]

    r = client.delete(f"/admin/firms/{firm_id}/tenants/{tenant_id}", headers=auth_headers)
    assert r.status_code == 204

    r = client.get(f"/admin/firms/{firm_id}/tenants", headers=auth_headers)
    ids = [t["id"] for t in r.json()]
    assert tenant_id not in ids


def test_api_create_tenant_firm_not_found(client, auth_headers):
    r = client.post(
        "/admin/firms/99999/tenants",
        json={"name": "Ghost Tenant"},
        headers=auth_headers,
    )
    assert r.status_code == 404


# ─── Audit log — API tests ────────────────────────────────────────────────────

def test_api_audit_log_populated_by_admin_actions(client, auth_headers):
    """Creating a firm should write an audit log entry accessible via the API."""
    client.post(
        "/admin/firms",
        json={"name": "Audit Firm", "slug": "audit-firm-slug"},
        headers=auth_headers,
    )
    r = client.get("/admin/audit-log?resource_type=firm", headers=auth_headers)
    assert r.status_code == 200
    entries = r.json()
    assert len(entries) >= 1
    assert entries[0]["resource_type"] == "firm"
    assert entries[0]["action"] == "create"


def test_api_audit_log_requires_audit_read(client, agent_headers):
    """Agent role lacks audit:read permission."""
    r = client.get("/admin/audit-log", headers=agent_headers)
    assert r.status_code == 403


def test_api_audit_log_filter_by_resource_type(client, auth_headers):
    r = client.get("/admin/audit-log?resource_type=nonexistent", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


# ─── Cross-tenant isolation — conceptual test ─────────────────────────────────

def test_tenant_id_header_injected_into_state(client, auth_headers):
    """X-Tenant-ID header should not break requests (middleware parses it)."""
    r = client.get(
        "/tax/records/",
        headers={**auth_headers, "X-Tenant-ID": "1"},
    )
    assert r.status_code == 200


def test_invalid_tenant_id_header_ignored(client, auth_headers):
    """Malformed X-Tenant-ID should not cause a 500 error."""
    r = client.get(
        "/tax/records/",
        headers={**auth_headers, "X-Tenant-ID": "not-an-integer"},
    )
    assert r.status_code == 200
