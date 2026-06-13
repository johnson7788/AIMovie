"""Test file upload endpoints."""


def test_upload_not_implemented(client):
    """POST /app/shortplay/api/Uploads/upload should return 501."""
    resp = client.post("/app/shortplay/api/Uploads/upload")
    assert resp.status_code == 501


def test_upload_chunk_check_stub(client):
    """POST /app/shortplay/api/drama/uploadChunkCheck stub."""
    resp = client.post("/app/shortplay/api/drama/uploadChunkCheck", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert "uploaded" in body["data"]


def test_upload_chunk_stub(client):
    """POST /app/shortplay/api/drama/uploadChunk stub."""
    resp = client.post("/app/shortplay/api/drama/uploadChunk", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200


def test_merge_chunks_stub(client):
    """POST /app/shortplay/api/drama/mergeChunks stub."""
    resp = client.post("/app/shortplay/api/drama/mergeChunks", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert "url" in body["data"]
