from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db.database import get_db_dep
from app.db.models import Interaction, Item, User
from app.main import app
from app.tests.conftest import _TestSession


def _session():
    s = _TestSession()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


@pytest.fixture(autouse=True)
def seed_test_data():
    s = _TestSession()
    try:
        if not s.query(User).filter(User.external_id == "rec_user_001").first():
            user = User(external_id="rec_user_001", segment="active")
            s.add(user)
            s.flush()
            for i in range(1, 11):
                ext_id = f"rec_movie_{i:03d}"
                item = s.query(Item).filter(Item.external_id == ext_id).first()
                if item is None:
                    item = Item(
                        external_id=ext_id, title=f"Test Movie {i}",
                        category="Drama", status="active", price=0.0,
                        attributes_json='{"year": 2020, "rating": 8.0, "description": "A test film"}',
                    )
                    s.add(item)
                    s.flush()
                if i <= 5:
                    s.add(Interaction(user_id=user.id, item_id=item.id, event_type="watch", weight=1.0))
        s.commit()
    finally:
        s.close()


@pytest.fixture
def client():
    app.dependency_overrides[get_db_dep] = _session
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def test_recommendations_returned(client):
    resp = client.get("/recommendations/rec_user_001?k=5")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    recs = body["data"]["recommendations"]
    assert isinstance(recs, list)
    assert len(recs) <= 5
    for rec in recs:
        assert "item_id" in rec
        assert "rank" in rec
        assert "model_version" in rec


def test_user_not_found(client):
    resp = client.get("/recommendations/ghost_user_99999?k=5")
    assert resp.status_code == 404


def test_model_status(client):
    resp = client.get("/models/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "popularity" in body["data"]


def test_train_endpoint(client):
    resp = client.post("/models/train")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert "models" in body["data"]


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["database"] in ("connected", "unreachable")
