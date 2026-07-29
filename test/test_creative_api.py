"""Test creative video generation API — full flow.

Run against a live backend: pytest test_creative_api.py -v
"""

import time
import pytest


class TestSubmitVideoTask:
    """POST /app/shortplay/api/Creative/video"""

    def test_submit_with_defaults(self, client):
        """Minimal request: only image_url."""
        resp = client.post("/app/shortplay/api/Creative/video", json={
            "image_url": "https://example.com/test.jpg",
        })
        data = resp.json()
        assert resp.status_code == 200
        assert data["code"] == 200
        assert "task_id" in data["data"]
        assert data["data"]["status"] == "pending"

    def test_submit_with_all_params(self, client):
        """Submit with every optional field filled."""
        resp = client.post("/app/shortplay/api/Creative/video", json={
            "image_url": "https://example.com/test.jpg",
            "prompt": "A cat walking in a garden, cinematic lighting.",
            "duration": 10,
            "resolution": "720p",
            "model_id": "2",
        })
        data = resp.json()
        assert resp.status_code == 200
        assert data["code"] == 200
        assert data["data"]["status"] == "pending"

    def test_submit_with_prompt_only(self, client):
        """Prompt without model_id, duration, resolution."""
        resp = client.post("/app/shortplay/api/Creative/video", json={
            "image_url": "https://example.com/test.jpg",
            "prompt": "Dancing robot.",
        })
        assert resp.status_code == 200
        assert resp.json()["code"] == 200

    def test_missing_image_url(self, client):
        """Missing required image_url should return error."""
        resp = client.post("/app/shortplay/api/Creative/video", json={
            "prompt": "Cat walking.",
        })
        assert resp.status_code in (422, 400, 200)
        if resp.status_code == 200:
            body = resp.json()
            assert body["code"] != 200 or "task_id" not in body.get("data", {})

    def test_empty_body(self, client):
        """Empty body should be rejected."""
        resp = client.post("/app/shortplay/api/Creative/video", json={})
        assert resp.status_code in (422, 400, 200)
        if resp.status_code == 200:
            assert resp.json()["code"] != 200

    @pytest.mark.parametrize("model_id", ["1", "2", "3", "4"])
    def test_all_models(self, client, model_id):
        """Submit task with each known model_id."""
        resp = client.post("/app/shortplay/api/Creative/video", json={
            "image_url": "https://example.com/test.jpg",
            "prompt": f"Test with model {model_id}.",
            "model_id": model_id,
        })
        assert resp.status_code == 200
        assert resp.json()["code"] == 200

    @pytest.mark.parametrize("duration", [5, 10])
    def test_valid_durations(self, client, duration):
        """Both 5s and 10s should be accepted."""
        resp = client.post("/app/shortplay/api/Creative/video", json={
            "image_url": "https://example.com/test.jpg",
            "duration": duration,
        })
        assert resp.status_code == 200
        assert resp.json()["code"] == 200

    @pytest.mark.parametrize("resolution", ["1080p", "720p"])
    def test_valid_resolutions(self, client, resolution):
        """Both resolutions should be accepted."""
        resp = client.post("/app/shortplay/api/Creative/video", json={
            "image_url": "https://example.com/test.jpg",
            "resolution": resolution,
        })
        assert resp.status_code == 200
        assert resp.json()["code"] == 200

    def test_multiple_requests(self, client):
        """Submit multiple tasks should each get unique task_ids."""
        task_ids = set()
        for i in range(3):
            resp = client.post("/app/shortplay/api/Creative/video", json={
                "image_url": f"https://example.com/test_{i}.jpg",
                "prompt": f"Test {i}.",
            })
            assert resp.status_code == 200
            tid = resp.json()["data"]["task_id"]
            assert tid not in task_ids, "task_ids must be unique"
            task_ids.add(tid)


class TestTaskIndex:
    """GET /app/model/api/Task/index"""

    def test_list_tasks_default(self, client):
        """List creative_video tasks with defaults."""
        resp = client.get("/app/model/api/Task/index", params={
            "scene": "creative_video",
        })
        data = resp.json()
        assert resp.status_code == 200
        assert data["code"] == 200
        assert "data" in data["data"]
        assert isinstance(data["data"]["data"], list)
        assert "total" in data["data"]

    def test_list_tasks_with_pagination(self, client):
        """Pagination: limit and page."""
        resp = client.get("/app/model/api/Task/index", params={
            "scene": "creative_video",
            "limit": 5,
            "page": 1,
        })
        data = resp.json()
        assert resp.status_code == 200
        assert data["code"] == 200
        assert len(data["data"]["data"]) <= 5
        assert data["data"]["limit"] == 5
        assert data["data"]["page"] == 1

    def test_list_empty_page(self, client):
        """A far-out page should return empty list."""
        resp = client.get("/app/model/api/Task/index", params={
            "scene": "creative_video",
            "limit": 5,
            "page": 9999,
        })
        data = resp.json()
        assert resp.status_code == 200
        assert data["code"] == 200
        assert data["data"]["data"] == []

    def test_submitted_task_appears_in_index(self, client):
        """Submit a task → query Task/index → submitted task_id should appear."""
        # Submit
        resp = client.post("/app/shortplay/api/Creative/video", json={
            "image_url": "https://example.com/verify.jpg",
            "prompt": "Verification task.",
        })
        task_id = resp.json()["data"]["task_id"]

        # Query
        resp = client.get("/app/model/api/Task/index", params={
            "scene": "creative_video",
            "limit": 50,
        })
        tasks = resp.json()["data"]["data"]
        task_ids = [t["task_id"] for t in tasks]
        assert task_id in task_ids, (
            f"Submitted task {task_id} not found in Task/index"
        )

    def test_task_status_transition(self, client):
        """Task status should go from pending to completed or failed."""
        # Submit
        resp = client.post("/app/shortplay/api/Creative/video", json={
            "image_url": "https://example.com/transition.jpg",
            "prompt": "Status transition test.",
        })
        task_id = resp.json()["data"]["task_id"]

        # Wait up to 60 seconds for task to leave 'pending' state
        deadline = time.time() + 60
        final_status = None
        while time.time() < deadline:
            resp = client.get("/app/model/api/Task/index", params={
                "scene": "creative_video",
                "limit": 100,
            })
            for t in resp.json()["data"]["data"]:
                if t["task_id"] == task_id:
                    final_status = t["status"]
                    break
            if final_status != "pending":
                break
            time.sleep(3)

        assert final_status is not None, "Task not found in index"
        assert final_status != "pending", (
            f"Task still pending after 60s, check backend generator config"
        )
        # completed or failed are both valid terminal states
        assert final_status in ("completed", "failed")


class TestResponseEnvelope:
    """Both endpoints follow the standard success/error envelope."""

    def test_creative_video_envelope(self, client):
        """Creative/video returns {code, data, msg}."""
        resp = client.post("/app/shortplay/api/Creative/video", json={
            "image_url": "https://example.com/test.jpg",
        })
        body = resp.json()
        assert "code" in body
        assert "data" in body
        assert "msg" in body
        assert isinstance(body["code"], int)

    def test_task_index_envelope(self, client):
        """Task/index returns {code, data, msg}."""
        resp = client.get("/app/model/api/Task/index", params={
            "scene": "creative_video",
        })
        body = resp.json()
        assert "code" in body
        assert "data" in body
        assert "msg" in body
