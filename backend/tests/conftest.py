from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def session_factory():
    temporary_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temporary_db.close()
    database_path = Path(temporary_db.name)

    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    Base.metadata.create_all(engine)

    try:
        yield SessionLocal
    finally:
        engine.dispose()
        database_path.unlink(missing_ok=True)


@pytest.fixture()
def db_session(session_factory) -> Session:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def api_client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
