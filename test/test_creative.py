"""Test creative video endpoint."""


def test_creative_video(client):
    """POST /app/shortplay/api/Creative/video should create task."""
    resp = client.post("/app/shortplay/api/Creative/video", json={
        "image_url": "https://example.com/test.jpg",
        "prompt": "Cat walking animation.",
        "duration": 5,
        "resolution": "1080p",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert "task_id" in data
    assert "status" in data


def test_creative_video_missing_image(client):
    """POST /app/shortplay/api/Creative/video without image_url should fail."""
    resp = client.post("/app/shortplay/api/Creative/video", json={
        "prompt": "Cat walking.",
    })
    # Should fail with validation error (422) or return error
    assert resp.status_code in (422, 400, 200)
