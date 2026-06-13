"""Test health check endpoint."""


def test_health(client):
    """GET /health should return status ok."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"status": "ok"}
