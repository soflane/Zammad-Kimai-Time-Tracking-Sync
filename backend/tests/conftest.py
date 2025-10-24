import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal, get_db

# Override dependency for test database session (rollback after each test)
def override_get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
