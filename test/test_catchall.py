"""Test catch-all fallback endpoint."""


def test_catch_all_unknown_endpoint(client):
    """GET /app/unknown/path should return 501."""
    resp = client.get("/app/unknown/endpoint/that/does/not/exist")
    assert resp.status_code == 501
    assert "not implemented" in resp.text.lower()


def test_catch_all_post(client):
    """POST /app/unknown/path should return 501."""
    resp = client.post("/app/unknown/endpoint", json={})
    assert resp.status_code == 501


def test_root_not_found(client):
    """GET / should return 404 (no root endpoint defined)."""
    resp = client.get("/")
    assert resp.status_code == 404
