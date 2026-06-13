"""Test generation endpoints."""


def test_generate_scene_image(client):
    """POST /app/shortplay/api/Generate/sceneImage should create task."""
    resp = client.post("/app/shortplay/api/Generate/sceneImage", json={
        "prompt": "A cozy bookshop with warm golden lamplight.",
        "model_id": "1",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert "task_id" in data
    assert "status" in data


def test_generate_storyboard_image(client):
    """POST /app/shortplay/api/Generate/storyboardImage should create task."""
    resp = client.post("/app/shortplay/api/Generate/storyboardImage", json={
        "prompt": "Wide shot of a cat entering a bookshop.",
        "model_id": "1",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert "task_id" in body["data"]


def test_generate_storyboard_video(client):
    """POST /app/shortplay/api/Generate/storyboardVideo should create task."""
    resp = client.post("/app/shortplay/api/Generate/storyboardVideo", json={
        "prompt": "Cat walking through bookshop aisles.",
        "duration": 5,
        "model_id": "1",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert "task_id" in body["data"]


def test_generate_character_look(client):
    """POST /app/shortplay/api/Generate/characterLook should create task."""
    resp = client.post("/app/shortplay/api/Generate/characterLook", json={
        "prompt": "An orange tabby cat character.",
        "model_id": "1",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert "task_id" in body["data"]


def test_generate_drama_cover(client):
    """POST /app/shortplay/api/Generate/dramaCover should create task."""
    resp = client.post("/app/shortplay/api/Generate/dramaCover", json={
        "prompt": "A mysterious bookshop at night.",
        "model_id": "1",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert "task_id" in body["data"]
