"""Integration tests for the actor (演员库) endpoints.

These run against a live server (see conftest BASE_URL).
"""
import base64

from conftest import auth_headers

# 1x1 transparent PNG
_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8AAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
)


def _create_actor(client, token, **overrides):
    payload = {
        "name": "测试演员",
        "species_type": 1,
        "gender": 1,
        "age": 2,
        "remarks": "短发男青年，穿黑色风衣",
    }
    payload.update(overrides)
    resp = client.post(
        "/app/shortplay/api/Actor/update", json=payload, headers=auth_headers(token)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200, body
    assert body["data"]["id"]
    return body["data"]


def test_actor_index_no_auth_returns_empty(client):
    resp = client.get("/app/shortplay/api/Actor/index")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["data"] == []


def test_actor_create_list_delete(client, auth_token):
    actor = _create_actor(client, auth_token, name="增删查演员")
    actor_id = actor["id"]
    assert actor["is_edit"] is True
    assert actor["status_enum"]["value"] == "initializing"

    # appears in personal list
    resp = client.get(
        "/app/shortplay/api/Actor/index",
        params={"type": "personal"},
        headers=auth_headers(auth_token),
    )
    data = resp.json()["data"]
    assert any(a["id"] == actor_id and a["name"] == "增删查演员" for a in data)

    # delete
    resp = client.post(
        "/app/shortplay/api/Actor/delete",
        json={"id": actor_id},
        headers=auth_headers(auth_token),
    )
    assert resp.json()["code"] == 200

    # gone
    resp = client.get(
        "/app/shortplay/api/Actor/index",
        params={"type": "personal"},
        headers=auth_headers(auth_token),
    )
    assert all(a["id"] != actor_id for a in resp.json()["data"])


def test_actor_edit_updates_fields(client, auth_token):
    actor = _create_actor(client, auth_token, name="原名")
    resp = client.post(
        "/app/shortplay/api/Actor/update",
        json={"id": actor["id"], "name": "改名", "species_type": 3, "remarks": "机甲战士"},
        headers=auth_headers(auth_token),
    )
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["id"] == actor["id"]
    assert body["data"]["name"] == "改名"
    assert body["data"]["species_type"] == 3
    client.post(
        "/app/shortplay/api/Actor/delete",
        json={"id": actor["id"]},
        headers=auth_headers(auth_token),
    )


def test_actor_filter_by_species(client, auth_token):
    a1 = _create_actor(client, auth_token, name="人类甲", species_type=1)
    a2 = _create_actor(client, auth_token, name="动物乙", species_type=2)
    resp = client.get(
        "/app/shortplay/api/Actor/index",
        params={"type": "personal", "species_type": 2},
        headers=auth_headers(auth_token),
    )
    data = resp.json()["data"]
    ids = {a["id"] for a in data}
    assert a2["id"] in ids
    assert a1["id"] not in ids
    for aid in (a1["id"], a2["id"]):
        client.post(
            "/app/shortplay/api/Actor/delete",
            json={"id": aid},
            headers=auth_headers(auth_token),
        )


def test_actor_delete_requires_owner(client, auth_token):
    resp = client.post(
        "/app/shortplay/api/Actor/delete",
        json={"id": "nonexistent-id"},
        headers=auth_headers(auth_token),
    )
    assert resp.json()["code"] == 404


def test_actor_initializing_requires_auth(client):
    resp = client.post("/app/shortplay/api/Actor/initializing", json={"id": "x"})
    assert resp.status_code == 401


def test_actor_initializing_missing_id(client, auth_token):
    resp = client.post(
        "/app/shortplay/api/Actor/initializing",
        json={},
        headers=auth_headers(auth_token),
    )
    assert resp.json()["code"] == 400


def test_actor_initializing_requires_model(client, auth_token):
    """No model selected -> rejected before any image API is touched."""
    actor = _create_actor(client, auth_token, name="待出图")
    resp = client.post(
        "/app/shortplay/api/Actor/initializing",
        json={"id": actor["id"]},
        headers=auth_headers(auth_token),
    )
    assert resp.json()["code"] == 400
    client.post(
        "/app/shortplay/api/Actor/delete",
        json={"id": actor["id"]},
        headers=auth_headers(auth_token),
    )


# --- Uploads ---
def test_upload_image_and_serve(client, auth_token):
    resp = client.post(
        "/app/shortplay/api/Uploads/upload",
        files={"file": ("a.png", _PNG_BYTES, "image/png")},
        data={"dir_name": "actor/image", "dir_title": "演员图片"},
        headers=auth_headers(auth_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["dir_name"] == "actor/image"
    assert data["url"].startswith("/api/uploads/actor/image/")

    # the file is served back
    served = client.get(data["url"])
    assert served.status_code == 200


def test_upload_rejects_non_image(client, auth_token):
    resp = client.post(
        "/app/shortplay/api/Uploads/upload",
        files={"file": ("a.txt", b"hello", "text/plain")},
        data={"dir_name": "actor/image"},
        headers=auth_headers(auth_token),
    )
    assert resp.json()["code"] == 400


def test_upload_rejects_bad_dir(client, auth_token):
    resp = client.post(
        "/app/shortplay/api/Uploads/upload",
        files={"file": ("a.png", _PNG_BYTES, "image/png")},
        data={"dir_name": "../../etc"},
        headers=auth_headers(auth_token),
    )
    assert resp.json()["code"] == 400


def test_upload_requires_auth(client):
    resp = client.post(
        "/app/shortplay/api/Uploads/upload",
        files={"file": ("a.png", _PNG_BYTES, "image/png")},
        data={"dir_name": "actor/image"},
    )
    assert resp.status_code == 401
