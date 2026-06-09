from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db.database import get_db_dep
from app.db.models import Item, User
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
        if not s.query(User).filter(User.external_id == "test_user_001").first():
            s.add(User(external_id="test_user_001", segment="active"))
        if not s.query(Item).filter(Item.external_id == "test_item_001").first():
            s.add(Item(external_id="test_item_001", title="Test Movie",
                       category="Drama", status="active", price=0.0))
        s.commit()
    finally:
        s.close()


@pytest.fixture
def client():
    app.dependency_overrides[get_db_dep] = _session
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def test_record_event(client):
    resp = client.post("/events", json={
        "user_external_id": "test_user_001",
        "item_external_id": "test_item_001",
        "event_type": "watch",
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["event_type"] == "watch"
    assert body["data"]["weight"] == 1.0


def test_record_event_invalid_type(client):
    resp = client.post("/events", json={
        "user_external_id": "test_user_001",
        "item_external_id": "test_item_001",
        "event_type": "invalid_type",
    })
    assert resp.status_code == 422


def test_record_event_missing_item(client):
    resp = client.post("/events", json={
        "user_external_id": "test_user_001",
        "item_external_id": "nonexistent_item",
        "event_type": "click",
    })
    assert resp.status_code == 404


def test_list_events(client):
    client.post("/events", json={
        "user_external_id": "test_user_001",
        "item_external_id": "test_item_001",
        "event_type": "view",
    })
    resp = client.get("/events?page=1&page_size=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


def test_creates_new_user_on_event(client):
    resp = client.post("/events", json={
        "user_external_id": "brand_new_user_xyz",
        "item_external_id": "test_item_001",
        "event_type": "view",
    })
    assert resp.status_code == 201
    assert resp.json()["data"]["user_external_id"] == "brand_new_user_xyz"
