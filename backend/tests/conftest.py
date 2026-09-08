import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base
from app.db.seed_helper import seed_demo_data
from app.db.session import get_db
from app.main import app

from sqlalchemy.pool import StaticPool

TEST_DB_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as db:
        seed_demo_data(db)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def disable_external_llm_for_tests():
    from app.core.config import get_settings
    settings = get_settings()
    orig_key = settings.openai_api_key
    settings.openai_api_key = ""
    yield
    settings.openai_api_key = orig_key


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
