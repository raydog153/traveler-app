from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.services import geocoding

# In-memory SQLite, shared across connections for the life of the engine --
# API tests exercise real router -> DB round-trips without touching the
# Postgres dev database that docker-compose wires up via DATABASE_URL.
_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
_TestSessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    Base.metadata.create_all(_engine)
    session = _TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(_engine)


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def stub_geocoding(monkeypatch: pytest.MonkeyPatch) -> None:
    """API tests never hit the real Nominatim API: fixed coordinates for
    every query, and no rate-limit sleep between fill-ups within a test."""
    geocoding._last_request_time = 0.0

    class FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> list[dict]:
            return [{"lat": "41.8781", "lon": "-87.6298"}]

    monkeypatch.setattr(geocoding.httpx, "get", lambda *a, **k: FakeResponse())
