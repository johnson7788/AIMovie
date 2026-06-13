"""Test core pipeline endpoints."""
import time


def test_get_models(client):
    """GET /api/models should return available AI models."""
    resp = client.get("/api/models")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert isinstance(data, dict)
    assert "creative_script" in data
    assert len(data["creative_script"]) > 0


def test_get_styles(client):
    """GET /api/styles should return available visual styles."""
    resp = client.get("/api/styles")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert isinstance(data, list)
    assert len(data) > 0
    assert "id" in data[0]
    assert "name" in data[0]


def test_get_config(client):
    """GET /api/config should return site configuration."""
    resp = client.get("/api/config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert "web_name" in data
    assert "web_title" in data
    assert "copyright" in data


def test_list_tasks(client):
    """GET /api/tasks should return task list."""
    resp = client.get("/api/tasks")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert isinstance(body["data"], list)


def test_get_nonexistent_task(client):
    """GET /api/tasks/{task_id} with fake ID should return 200 with null or 404."""
    resp = client.get("/api/tasks/fake-task-id-12345")
    assert resp.status_code in (200, 404)


def test_script2video_submit(client):
    """POST /api/script2video should create a task."""
    resp = client.post("/api/script2video", json={
        "script": "A cat explores a bookshop.",
        "style": "Cinematic",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert "task_id" in data
    assert data["mode"] == "script2video"

    # Check task was created
    time.sleep(1)
    resp = client.get(f"/api/tasks/{data['task_id']}")
    assert resp.status_code == 200


def test_idea2video_submit(client):
    """POST /api/idea2video should create a task."""
    resp = client.post("/api/idea2video", json={
        "idea": "A curious orange tabby cat explores a cozy old bookshop.",
        "style": "Anime",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert "task_id" in data
    assert data["mode"] == "idea2video"
