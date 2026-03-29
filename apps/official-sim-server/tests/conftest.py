import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient


TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/official_sim"


@pytest.fixture(scope="function")
def test_db():
    test_engine = create_engine(TEST_DATABASE_URL)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    from app.core.database import Base
    from app.models.models import (
        SimulationRun,
        SimulationEvent,
        StateSnapshot,
        PushEvent,
        Artifact,
        EvaluationReport,
    )

    Base.metadata.create_all(bind=test_engine)

    session = TestingSessionLocal()
    try:
        yield session, test_engine
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(test_db):
    session, test_engine = test_db

    from app.core.database import get_db
    from app.main import app

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
