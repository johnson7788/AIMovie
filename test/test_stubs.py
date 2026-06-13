"""Test stub/placeholder endpoints."""


def test_actor_index(client):
    """GET /app/shortplay/api/Actor/index should return empty list."""
    resp = client.get("/app/shortplay/api/Actor/index", params={
        "type": "all",
        "name": "",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert isinstance(body["data"], list)


def test_prop_index(client):
    """GET /app/shortplay/api/Prop/index should return empty list."""
    resp = client.get("/app/shortplay/api/Prop/index")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert isinstance(body["data"], list)


def test_works_index(client):
    """GET /app/shortplay/api/Works/index should return empty list."""
    resp = client.get("/app/shortplay/api/Works/index")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert "data" in data
    assert "total" in data


def test_works_details(client):
    """GET /app/shortplay/api/Works/details should return empty dict."""
    resp = client.get("/app/shortplay/api/Works/details")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200


def test_works_episode(client):
    """GET /app/shortplay/api/Works/episode should return empty list."""
    resp = client.get("/app/shortplay/api/Works/episode")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert "data" in data
    assert "total" in data


def test_scene_index(client):
    """GET /app/shortplay/api/Scene/index should return empty list."""
    resp = client.get("/app/shortplay/api/Scene/index")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert isinstance(body["data"], list)


def test_storyboard_index(client):
    """GET /app/shortplay/api/Storyboard/index should return empty list."""
    resp = client.get("/app/shortplay/api/Storyboard/index")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert isinstance(body["data"], list)


def test_storyboard_dialogue_index(client):
    """GET /app/shortplay/api/StoryboardDialogue/index should return empty list."""
    resp = client.get("/app/shortplay/api/StoryboardDialogue/index")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert isinstance(body["data"], list)


def test_character_look_index(client):
    """GET /app/shortplay/api/CharacterLook/index should return empty list."""
    resp = client.get("/app/shortplay/api/CharacterLook/index")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert isinstance(body["data"], list)


def test_square_details(client):
    """GET /app/shortplay/api/Square/details should return empty dict."""
    resp = client.get("/app/shortplay/api/Square/details")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200


def test_square_episodes(client):
    """GET /app/shortplay/api/Square/episodes should return empty list."""
    resp = client.get("/app/shortplay/api/Square/episodes")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert "data" in data
    assert "total" in data


def test_article_index(client):
    """GET /app/article/api/Article/index should return empty list."""
    resp = client.get("/app/article/api/Article/index")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert "data" in data
    assert "total" in data


def test_article_details(client):
    """GET /app/article/api/Article/details should return empty dict."""
    resp = client.get("/app/article/api/Article/details")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200


def test_message_list(client):
    """GET /app/notification/api/Message/list should return empty list."""
    resp = client.get("/app/notification/api/Message/list")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert "data" in data
    assert "total" in data


def test_message_detail(client):
    """GET /app/notification/api/Message/detail should return empty dict."""
    resp = client.get("/app/notification/api/Message/detail")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
