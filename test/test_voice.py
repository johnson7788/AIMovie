"""Test voice endpoints."""


def test_voice_model_list(client):
    """GET /app/model/api/Voice/modelList should return voice models."""
    resp = client.get("/app/model/api/Voice/modelList")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert isinstance(data, list)
    assert len(data) > 0
    # Check voice model structure
    assert "id" in data[0]
    assert "name" in data[0]


def test_voice_list(client):
    """GET /app/shortplay/api/Voice/list should return voice list."""
    resp = client.get("/app/shortplay/api/Voice/list")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert "data" in data or isinstance(data, list)
    assert "total" in data


def test_voice_update_stub(client):
    """POST /app/model/api/Voice/update is a stub."""
    resp = client.post("/app/model/api/Voice/update", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200


def test_voice_submit_stub(client):
    """POST /app/model/api/Voice/submit is a stub."""
    resp = client.post("/app/model/api/Voice/submit", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200


def test_voice_text_index_stub(client):
    """GET /app/model/api/VoiceText/index is a stub."""
    resp = client.get("/app/model/api/VoiceText/index")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert "data" in data
    assert "total" in data
