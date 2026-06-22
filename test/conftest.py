"""Shared fixtures and utilities for API tests."""
import os

import pytest
import httpx

BASE_URL = os.environ.get("TEST_BASE_URL", "http://127.0.0.1:8666")


@pytest.fixture(scope="session")
def client():
    """Reusable HTTP client for all tests."""
    with httpx.Client(base_url=BASE_URL, timeout=30) as c:
        yield c


@pytest.fixture(scope="session")
def auth_token(client):
    """Login and return a valid auth token."""
    import uuid
    suffix = uuid.uuid4().hex[:6]
    username = f"pytest_{suffix}"
    password = "pytest1234"

    # Register a fresh user
    resp = client.post("/app/user/api/Login/register", json={
        "username": username,
        "password": password,
        "vpassword": password,
    })
    data = resp.json()
    if data.get("code") == 200 and data.get("data", {}).get("token"):
        return data["data"]["token"]

    # Fallback: login with admin
    resp = client.post("/app/user/api/Login/login", json={
        "username": "admin",
        "password": "admin123",
    })
    data = resp.json()
    if data.get("code") == 200 and data.get("data", {}).get("token"):
        return data["data"]["token"]

    pytest.skip("Could not obtain auth token")


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def assert_ok(resp: httpx.Response, *, check_data=True):
    """Assert standard success envelope."""
    assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:300]}"
    body = resp.json()
    assert body["code"] == 200, f"code={body['code']}, msg={body.get('msg')}"
    if check_data:
        assert "data" in body
    return body["data"]
