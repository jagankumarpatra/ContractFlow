import os
import pytest

os.environ["DATABASE_URL"] = "sqlite:///./test_contractflow.db"
os.environ["SECRET_KEY"] = "test-secret-key-minimum-32-characters-long-yes"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["ANTHROPIC_API_KEY"] = ""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

TEST_DB_URL = "sqlite:///./test_contractflow.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Patch BEFORE any app module imports
import app.db.base as db_module
db_module.engine = test_engine
db_module.SessionLocal = TestSession

from app.main import app
from app.db.base import Base, get_db

def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create all tables once at session start
Base.metadata.create_all(bind=test_engine)

@pytest.fixture(autouse=True)
def clean_db():
    """Delete all rows between tests (faster than drop/recreate)."""
    from app.models.contract import Contract
    from app.models.user import User
    from app.models.company import Company
    yield
    db = TestSession()
    try:
        db.query(Contract).delete()
        db.query(User).delete()
        db.query(Company).delete()
        db.commit()
    finally:
        db.close()

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    return TestClient(app)

@pytest.fixture
def registered_user(client):
    res = client.post("/api/v1/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123",
        "company_name": "Test Company"
    })
    assert res.status_code == 201, f"Register failed: {res.json()}"
    return res.json()

@pytest.fixture
def auth_headers(registered_user):
    return {"Authorization": f"Bearer {registered_user['access_token']}"}

@pytest.fixture
def sample_contract(client, auth_headers):
    res = client.post("/api/v1/contracts/", json={
        "title": "Sample NDA Agreement",
        "contract_type": "nda",
        "party_a": "Test Company",
        "party_b": "Partner Corp",
        "contract_text": "This Non-Disclosure Agreement is entered into between parties..."
    }, headers=auth_headers)
    assert res.status_code == 201, f"Contract create failed: {res.json()}"
    return res.json()
