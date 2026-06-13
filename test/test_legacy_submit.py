"""Test legacy frontend submit endpoint."""
import time


def test_legacy_submit_script_mode(client):
    """POST /app/shortplay/api/Index/submit with script mode."""
    resp = client.post("/app/shortplay/api/Index/submit", json={
        "model": "1",
        "script": "script",
        "prompt": "A cat in a bookshop.",
        "style": "cinematic",
        "aspect_ratio": "9:16",
        "episode_sum": 2,
        "episode_duration": 60,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert "task_id" in data
    assert "uuid" in data
    assert data["mode"] == "script2video"

    # Check task was created
    time.sleep(1)
    task_id = data["task_id"]
    resp = client.get(f"/api/tasks/{task_id}")
    assert resp.status_code == 200


def test_legacy_submit_drama_mode(client):
    """POST /app/shortplay/api/Index/submit with drama mode (idea2video)."""
    resp = client.post("/app/shortplay/api/Index/submit", json={
        "model": "2",
        "script": "drama",
        "prompt": "A space adventure story.",
        "style": "anime",
        "episode_sum": 3,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["mode"] == "idea2video"


def test_legacy_models_alias(client):
    """GET /app/model/api/Model/models should be alias for /api/models."""
    resp = client.get("/app/model/api/Model/models")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert "creative_script" in data


def test_legacy_styles_with_filter(client):
    """GET /app/shortplay/api/Style/index with query filters."""
    # Get all styles
    resp = client.get("/app/shortplay/api/Style/index", params={
        "classify": "all",
        "name": "",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert isinstance(body["data"], list)

    # Filter by classify
    resp = client.get("/app/shortplay/api/Style/index", params={
        "classify": "anime",
        "name": "",
    })
    assert resp.status_code == 200
    body = resp.json()
    anime_styles = body["data"]
    for style in anime_styles:
        assert style["classify"] == "anime"
