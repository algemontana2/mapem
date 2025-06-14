# test/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import create_app
from backend.models import Base
import backend.db  # so we can patch SessionLocal + engine
import os
from pathlib import Path


@pytest.fixture(scope="session")
def app():
    # Create a test DB engine (in-memory SQLite)
    test_engine = create_engine("sqlite:///:memory:", future=True)
    TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, future=True)

    # Patch the app-wide engine/session before app creation
    backend.db.engine = test_engine
    backend.db.SessionLocal = TestingSessionLocal
    backend.db.get_engine.cache_clear()
    backend.db.get_sessionmaker.cache_clear()
    backend.db.get_engine = lambda db_uri=None: test_engine
    backend.db.get_sessionmaker = lambda db_uri=None: TestingSessionLocal

    app = create_app()
    app.config.update({
        "TESTING": True
    })

    # Set up schema
    Base.metadata.create_all(bind=test_engine)
    yield app
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def db_session():
    db = backend.db.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def gedcom_path():
    # adjust if your test file lives somewhere else
    return Path(__file__).parent / "data/test_family_events.ged"


@pytest.fixture
def dummy_location_service():
    class Dummy:
        def resolve_location(self, **kwargs):
            class Out:
                normalized_name   = "dummy_loc"
                raw_name          = "Dummy, Loc"
                latitude          = 1.0
                longitude         = 2.0
                confidence_score  = 1.0
                status            = "ok"
                source            = "test"
            return Out()
    return Dummy()
