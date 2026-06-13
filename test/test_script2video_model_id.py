"""Test that legacy submit correctly passes model_id to script2video pipeline.

Regression test: when submitting via /app/shortplay/api/Index/submit with
script="script" and model="5" (GPUGeek), the task used to fail with:
  "The api_key client option must be set either by passing api_key to the
   client or by setting the OPENAI_API_KEY environment variable"

This happened because the script2video path ignored the selected model and
always used the default script2video.yaml config (openai provider).
"""
import time


def test_script2video_passes_model_id(client):
    """Legacy submit with script mode should forward model_id to pipeline."""
    # Submit with model "5" (GPUGeek / DeepSeek V4)
    resp = client.post("/app/shortplay/api/Index/submit", json={
        "model": "5",
        "script": "script",
        "prompt": "A cat in a bookshop.",
        "style": "storybook",
        "aspect_ratio": "9:16",
        "episode_sum": 3,
        "episode_duration": 60,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    task_id = body["data"]["task_id"]
    assert body["data"]["mode"] == "script2video"

    # Wait for the task to fail (no API keys configured)
    time.sleep(3)

    resp = client.get(f"/api/tasks/{task_id}")
    assert resp.status_code == 200
    task = resp.json()["data"]
    assert task["task_id"] == task_id

    # The task may be pending/running/failed, but if it failed, the error
    # should NOT mention OPENAI_API_KEY since we selected a GPUGeek model.
    if task["status"] == "failed" and task.get("error"):
        error_msg = task["error"]
        assert "OPENAI_API_KEY" not in error_msg, (
            f"Bug regression: script2video with model=5 (GPUGeek) still uses "
            f"OpenAI provider. Error: {error_msg}"
        )


def test_script2video_different_models_use_correct_provider(client):
    """Each creative_script model should use its own provider, not always openai."""
    # Get available models
    resp = client.get("/app/model/api/Model/models")
    models = resp.json()["data"]["creative_script"]
    assert len(models) > 0

    for model in models:
        model_id = model["id"]
        provider = model["provider"]

        # Submit a task with this model
        resp = client.post("/app/shortplay/api/Index/submit", json={
            "model": model_id,
            "script": "script",
            "prompt": "Test prompt.",
            "style": "cinematic",
        })
        assert resp.status_code == 200
        task_id = resp.json()["data"]["task_id"]

        # Wait for it to process
        time.sleep(2)

        resp = client.get(f"/api/tasks/{task_id}")
        task = resp.json()["data"]

        if task["status"] == "failed" and task.get("error"):
            error_msg = task["error"]
            # The error should not mention a wrong provider's API key
            # e.g., GPUGeek model should not fail with OPENAI_API_KEY
            if provider == "gpugeek":
                assert "OPENAI_API_KEY" not in error_msg, (
                    f"Model {model['name']} (provider={provider}) incorrectly "
                    f"uses OpenAI provider. Error: {error_msg}"
                )
            elif provider == "volcengine":
                assert "OPENAI_API_KEY" not in error_msg, (
                    f"Model {model['name']} (provider={provider}) incorrectly "
                    f"uses OpenAI provider. Error: {error_msg}"
                )


def test_script2video_model_id_in_cache_key(client):
    """Different model_ids should produce different task cache keys."""
    # Submit same script with two different models
    task_ids = []
    for model_id in ["1", "5"]:
        resp = client.post("/app/shortplay/api/Index/submit", json={
            "model": model_id,
            "script": "script",
            "prompt": "Identical prompt for cache test.",
            "style": "cinematic",
        })
        assert resp.status_code == 200
        task_ids.append(resp.json()["data"]["task_id"])

    # Both tasks should be created with different IDs
    assert task_ids[0] != task_ids[1]

    time.sleep(2)
    # Both should exist as separate tasks
    for tid in task_ids:
        resp = client.get(f"/api/tasks/{tid}")
        assert resp.status_code == 200
        assert resp.json()["data"]["task_id"] == tid
