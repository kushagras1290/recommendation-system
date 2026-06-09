"""
Configure tests to use an in-memory SQLite database instead of Postgres.
This conftest is loaded before any test module so the patching happens
before any database engine is created.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Must be set before any app module is imported
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_recsys.db")
os.environ.setdefault("CORS_ORIGINS", '["http://localhost:3000"]')
os.environ.setdefault("MODEL_DIR", "./test_model_artifacts")

from app.core.config import get_settings
get_settings.cache_clear()

from app.db import database as db_module
from app.db.database import Base

TEST_DB_URL = "sqlite:///./test_recsys.db"
_test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False}).execution_options(
    schema_translate_map={"recsys": None}
)
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)

# Patch the module-level engine before any test runs
db_module.reset_engine(_test_engine)


@pytest.fixture(autouse=True, scope="session")
def setup_test_db():
    from app.db import models  # noqa — register models
    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)
