"""
Wave 1 RBAC tests.
Covers: permission matrix, role assignment/revocation, cross-role isolation.
"""
import pytest
from app.rbac import user_has_permission, ROLE_PERMISSIONS
from app import models
from app.auth import hash_password


# ─── Unit: permission matrix ────────────────────────────────────────────────

class FakeUserRole:
    def __init__(self, role): self.role = role

class FakeUser:
    def __init__(self, roles):
        self.user_roles = [FakeUserRole(r) for r in roles]
    @property
    def roles(self): return [ur.role for ur in self.user_roles]


def test_admin_has_all_permissions():
    u = FakeUser(["admin"])
    for scope in ["filings:read", "filings:submit", "users:manage", "audit:read"]:
        assert user_has_permission(u, scope)


def test_auditor_read_only():
    u = FakeUser(["auditor"])
    assert user_has_permission(u, "filings:read")
    assert user_has_permission(u, "audit:read")
    assert not user_has_permission(u, "filings:write")
    assert not user_has_permission(u, "users:manage")
    assert not user_has_permission(u, "expenses:approve")


def test_agent_limited():
    u = FakeUser(["agent"])
    assert user_has_permission(u, "records:read")
    assert not user_has_permission(u, "records:write")
    assert not user_has_permission(u, "filings:submit")


def test_business_owner_cannot_manage_users():
    u = FakeUser(["business_owner"])
    assert not user_has_permission(u, "users:manage")
    assert user_has_permission(u, "records:write")


def test_accountant_can_approve_expenses():
    u = FakeUser(["accountant"])
    assert user_has_permission(u, "expenses:approve")
    assert not user_has_permission(u, "users:manage")


def test_multi_role_union():
    """A user with both agent and auditor gets the union of both role sets."""
    u = FakeUser(["agent", "auditor"])
    assert user_has_permission(u, "audit:read")   # from auditor
    assert user_has_permission(u, "records:read") # from both
    assert not user_has_permission(u, "records:write")


# ─── API: role assignment ────────────────────────────────────────────────────

def test_assign_role(client, auth_headers, db_session):
    # Create target user
    client.post("/auth/register", json={"username": "target_u", "password": "targetpass1"})

    r = client.post(
        "/users/roles/assign",
        json={"username": "target_u", "role": "accountant"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert r.json()["role"] == "accountant"


def test_assign_duplicate_role(client, auth_headers):
    client.post("/auth/register", json={"username": "dup_role_u", "password": "duppass123"})
    client.post(
        "/users/roles/assign",
        json={"username": "dup_role_u", "role": "agent"},
        headers=auth_headers,
    )
    r = client.post(
        "/users/roles/assign",
        json={"username": "dup_role_u", "role": "agent"},
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_revoke_role(client, auth_headers, db_session):
    client.post("/auth/register", json={"username": "revoke_u", "password": "revokepass1"})
    client.post(
        "/users/roles/assign",
        json={"username": "revoke_u", "role": "auditor"},
        headers=auth_headers,
    )
    r = client.post(
        "/users/roles/revoke",
        json={"username": "revoke_u", "role": "auditor"},
        headers=auth_headers,
    )
    assert r.status_code == 204


def test_revoke_nonexistent_role(client, auth_headers):
    client.post("/auth/register", json={"username": "norole_u", "password": "norolepass1"})
    r = client.post(
        "/users/roles/revoke",
        json={"username": "norole_u", "role": "agent"},
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_assign_role_requires_admin(client, agent_headers):
    client.post("/auth/register", json={"username": "victim_u", "password": "victimpass1"})
    r = client.post(
        "/users/roles/assign",
        json={"username": "victim_u", "role": "accountant"},
        headers=agent_headers,
    )
    assert r.status_code == 403


# ─── API: cross-role permission enforcement ──────────────────────────────────

def test_agent_cannot_write_records(client, agent_headers):
    r = client.post(
        "/tax/records/",
        json={"entity_name": "Test", "tax_year": 2024, "income": "10000"},
        headers=agent_headers,
    )
    assert r.status_code == 403


def test_agent_can_read_records(client, agent_headers, auth_headers):
    # Admin creates a record first
    client.post(
        "/tax/records/",
        json={"entity_name": "Readable Corp", "tax_year": 2024, "income": "50000"},
        headers=auth_headers,
    )
    r = client.get("/tax/records/", headers=agent_headers)
    assert r.status_code == 200


def test_auditor_cannot_write_records(client, auditor_headers):
    r = client.post(
        "/tax/records/",
        json={"entity_name": "Audit Test", "tax_year": 2024, "income": "10000"},
        headers=auditor_headers,
    )
    assert r.status_code == 403


def test_unauthenticated_is_401(client):
    r = client.get("/tax/records/")
    assert r.status_code == 401


def test_list_users_requires_admin(client, agent_headers):
    r = client.get("/users/", headers=agent_headers)
    assert r.status_code == 403


def test_list_users_as_admin(client, auth_headers):
    r = client.get("/users/", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_me(client, accountant_headers):
    r = client.get("/users/me", headers=accountant_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == "accountant_user"
    assert "accountant" in data["roles"]
