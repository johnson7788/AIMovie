"""Test control panel endpoints."""


def test_public_config(client):
    """GET /app/control/api/Public/config should return frontend config."""
    resp = client.get("/app/control/api/Public/config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]

    # Check required fields
    assert "web_name" in data
    assert "web_title" in data
    assert "copyright" in data
    assert "version" in data
    assert "version_name" in data

    # Check enums
    assert "enum" in data
    enums = data["enum"]
    assert "actor_species_type" in enums
    assert "actor_gender" in enums
    assert "actor_age" in enums
    assert "style_classify" in enums
    assert "voice_emotion" in enums

    # Check menu
    assert "showMenu" in data
    assert isinstance(data["showMenu"], list)


def test_sms_vcode_disabled(client):
    """POST /app/control/api/Public/getSmsVcode should be disabled."""
    resp = client.post("/app/control/api/Public/getSmsVcode", json={
        "mobile": "13800138000",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] != 200
