"""Test user and auth endpoints."""


def test_user_info_no_auth(client):
    """GET /app/user/api/User/info without auth should return guest."""
    resp = client.get("/app/user/api/User/info")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert "is_guest" in data


def test_register_and_login(client):
    """POST register then login should work."""
    import uuid
    suffix = uuid.uuid4().hex[:6]
    username = f"pytest_{suffix}"
    password = "pytest1234"

    # Register
    resp = client.post("/app/user/api/Login/register", json={
        "username": username,
        "password": password,
        "vpassword": password,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert "token" in body["data"]

    # Login with the same user
    resp = client.post("/app/user/api/Login/login", json={
        "username": username,
        "password": password,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert "token" in body["data"]
    assert body["data"]["username"] == username


def test_login_wrong_password(client):
    """POST /app/user/api/Login/login with wrong password should fail."""
    # Use admin user which should exist
    resp = client.post("/app/user/api/Login/login", json={
        "username": "admin",
        "password": "wrongpassword",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] != 200 or not body.get("data", {}).get("token")


def test_register_password_mismatch(client):
    """POST /app/user/api/Login/register with mismatched passwords should fail."""
    resp = client.post("/app/user/api/Login/register", json={
        "username": "testuser2",
        "password": "pass123",
        "vpassword": "pass456",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] != 200


def test_user_info_with_auth(client, auth_token):
    """GET /app/user/api/User/info with valid token should return user."""
    resp = client.get("/app/user/api/User/info", headers={
        "Authorization": f"Bearer {auth_token}",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert "username" in data
    assert "token" in data
    assert not data["is_guest"]


def test_user_update(client, auth_token):
    """POST /app/user/api/User/update should update nickname."""
    resp = client.post("/app/user/api/User/update", json={
        "nickname": "TestNickname",
    }, headers={
        "Authorization": f"Bearer {auth_token}",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200


def test_invitation_code_check(client):
    """GET /app/user/api/User/checkInvitationCode stub."""
    resp = client.get("/app/user/api/User/checkInvitationCode", params={
        "code": "TEST123",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200


def test_disabled_login_endpoints(client):
    """Disabled login endpoints should return errors."""
    # loginPass
    resp = client.post("/app/user/api/Login/loginPass", json={})
    assert resp.status_code == 200
    assert resp.json()["code"] != 200

    # loginSms
    resp = client.post("/app/user/api/Login/loginSms", json={})
    assert resp.status_code == 200
    assert resp.json()["code"] != 200

    # wechatLogin
    resp = client.post("/app/user/api/Login/wechatLogin", json={})
    assert resp.status_code == 200
    assert resp.json()["code"] != 200
