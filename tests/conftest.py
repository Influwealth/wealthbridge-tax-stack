import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app import models
from app.auth import hash_password

SQLALCHEMY_TEST_URL = "sqlite:///./test.db"


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("test.db"):
        os.remove("test.db")


@pytest.fixture(scope="function")
def db_session(db_engine):
    TestingSession = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = TestingSession()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _create_user_with_role(db_session, username: str, password: str, role: str):
    """Helper: create user + assign role directly in DB."""
    user = db_session.query(models.User).filter(models.User.username == username).first()
    if not user:
        user = models.User(username=username, hashed_password=hash_password(password))
        db_session.add(user)
        db_session.flush()

    existing_role = (
        db_session.query(models.UserRole)
        .filter(models.UserRole.user_id == user.id, models.UserRole.role == role)
        .first()
    )
    if not existing_role:
        db_session.add(models.UserRole(user_id=user.id, role=role))

    db_session.commit()
    db_session.refresh(user)
    return user


def _get_token(client, username: str, password: str) -> str:
    r = client.post("/auth/token", data={"username": username, "password": password})
    assert r.status_code == 200, f"Login failed for {username}: {r.json()}"
    return r.json()["access_token"]


@pytest.fixture
def admin_user(db_session):
    return _create_user_with_role(db_session, "admin_user", "adminpass123", "admin")


@pytest.fixture
def accountant_user(db_session):
    return _create_user_with_role(db_session, "accountant_user", "accountantpass123", "accountant")


@pytest.fixture
def business_owner_user(db_session):
    return _create_user_with_role(db_session, "biz_owner", "bizpass123", "business_owner")


@pytest.fixture
def agent_user(db_session):
    return _create_user_with_role(db_session, "agent_user", "agentpass123", "agent")


@pytest.fixture
def auditor_user(db_session):
    return _create_user_with_role(db_session, "auditor_user", "auditorpass123", "auditor")


@pytest.fixture
def auth_headers(client, admin_user):
    """Admin JWT headers — holds all permissions."""
    token = _get_token(client, "admin_user", "adminpass123")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def accountant_headers(client, accountant_user):
    token = _get_token(client, "accountant_user", "accountantpass123")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def agent_headers(client, agent_user):
    token = _get_token(client, "agent_user", "agentpass123")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auditor_headers(client, auditor_user):
    token = _get_token(client, "auditor_user", "auditorpass123")
    return {"Authorization": f"Bearer {token}"}
