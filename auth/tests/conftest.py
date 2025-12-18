"""
Pytest configuration and fixtures for authentication tests
"""
import pytest
import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import Base, get_db
from main import app
from models import User

load_dotenv()

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with database dependency override"""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def valid_user_data():
    """Valid test user data"""
    return {
        "email": "testuser@example.com",
        "name": "Test User",
        "password": "testpass123"
    }


@pytest.fixture
def valid_login_credentials():
    """Valid login credentials"""
    return {
        "email": "testuser@example.com",
        "password": "testpass"
    }


@pytest.fixture
def invalid_login_credentials():
    """Invalid login credentials"""
    return {
        "email": "wrong@example.com",
        "password": "wrongpass"
    }


@pytest.fixture
def create_test_user(test_db, valid_user_data):
    """Create a test user in the database"""
    from datetime import datetime
    user = User(
        email=valid_user_data["email"],
        name=valid_user_data["name"],
        password=valid_user_data["password"],  # In real app, this should be hashed
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def valid_token(client, valid_login_credentials):
    """Generate a valid access token"""
    response = client.post("/login", json=valid_login_credentials)
    if response.status_code == 200:
        return response.json()["access_token"]
    return None


@pytest.fixture
def auth_headers(valid_token):
    """Create authorization headers with valid token"""
    return {"Authorization": f"Bearer {valid_token}"}


@pytest.fixture
def expired_token(env_settings):
    """Generate an actually expired token for testing"""
    from jose import jwt
    
    expired_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    payload = {
        "sub": "testuser@example.com",
        "exp": expired_time
    }
    
    secret_key = env_settings["SECRET_KEY"]
    algorithm = env_settings["ALGORITHM"]
    
    return jwt.encode(payload, secret_key, algorithm=algorithm)


@pytest.fixture
def invalid_token():
    """An invalid/malformed token"""
    return "invalid.token.here"


@pytest.fixture
def env_settings():
    """Get environment settings for testing"""
    return {
        "SECRET_KEY": os.getenv("SECRET_KEY"),
        "ALGORITHM": os.getenv("ALGORITHM", "HS256").strip('"'),
        "ACCESS_TOKEN_EXPIRE_MINUTES": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    }
