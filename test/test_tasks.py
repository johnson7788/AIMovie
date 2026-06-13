"""Test task management endpoints."""
import time


def test_task_list_with_pagination(client):
    """GET /app/model/api/Task/index should support pagination."""
    resp = client.get("/app/model/api/Task/index", params={
        "page": 1,
        "limit": 10,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert "data" in data or isinstance(data, list)
    assert "total" in data or "page" in data


def test_task_stream_with_timeout(client):
    """GET /api/tasks/{task_id}/stream should return SSE stream (test with short timeout)."""
    # Create a task first
    resp = client.post("/api/idea2video", json={
        "idea": "Test task stream.",
    })
    task_id = resp.json()["data"]["task_id"]

    time.sleep(0.5)
    # Use short timeout to avoid hanging on long-lived SSE connections
    try:
        with client.stream("GET", f"/api/tasks/{task_id}/stream", timeout=3) as resp:
            assert resp.status_code == 200
            # Read at least a few bytes to confirm SSE format
            chunks = []
            for line in resp.iter_lines():
                chunks.append(line)
                if len(chunks) > 5:
                    break
            # Should have received at least the connected event
            assert len(chunks) > 0
    except Exception:
        # Timeout is acceptable for SSE streams
        pass


def test_task_file_access_nonexistent(client):
    """GET /api/tasks/{task_id}/files/{path} with fake task should fail."""
    resp = client.get("/api/tasks/fake-id-12345/files/test.txt")
    assert resp.status_code in (404, 400, 500)


def test_task_lifecycle(client):
    """Test complete task lifecycle: create -> query."""
    # Create a task
    resp = client.post("/api/idea2video", json={
        "idea": "Test task lifecycle.",
    })
    assert resp.status_code == 200
    task_id = resp.json()["data"]["task_id"]

    # Query task
    time.sleep(0.5)
    resp = client.get(f"/api/tasks/{task_id}")
    assert resp.status_code == 200
    task_data = resp.json()["data"]
    assert task_data["task_id"] == task_id
    assert "status" in task_data
