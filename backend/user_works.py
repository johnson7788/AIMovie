"""Persist completed generation tasks as user-visible works."""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional, Tuple


def init_works_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_works (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            task_id TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            prompt TEXT,
            cover TEXT,
            video_path TEXT,
            mode TEXT NOT NULL,
            episode_num INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_works_user_id ON user_works(user_id)"
    )

    for column in ("user_id", "title", "prompt"):
        try:
            conn.execute(f"ALTER TABLE tasks ADD COLUMN {column} TEXT")
        except sqlite3.OperationalError:
            pass


def _find_cover_relative_path(working_dir: Optional[str]) -> str:
    if not working_dir:
        return ""
    candidates = (
        "shots/0/first_frame.png",
        "scene_0/shots/0/first_frame.png",
        "scene_0/scene_anchor.png",
        "scene_anchor.png",
    )
    for relative in candidates:
        if os.path.exists(os.path.join(working_dir, relative)):
            return relative.replace("\\", "/")
    return ""


def _format_create_time(value: Optional[str]) -> str:
    if not value:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return str(value)[:16]


def create_work_from_task(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    task_id: str,
    title: str,
    prompt: str,
    mode: str,
    result_path: str,
    working_dir: Optional[str],
) -> dict:
    cover = _find_cover_relative_path(working_dir)
    video_path = "final_video.mp4"
    if result_path:
        normalized = result_path.replace("\\", "/")
        if normalized.endswith(".mp4"):
            basename = os.path.basename(normalized)
            if working_dir and normalized.startswith(os.path.abspath(working_dir)):
                video_path = os.path.relpath(normalized, working_dir).replace("\\", "/")
            elif basename:
                video_path = basename

    work_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT OR REPLACE INTO user_works (
            id, user_id, task_id, title, prompt, cover, video_path, mode, episode_num
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (work_id, user_id, task_id, title, prompt, cover, video_path, mode),
    )
    row = conn.execute(
        "SELECT * FROM user_works WHERE task_id = ?", (task_id,)
    ).fetchone()
    return _row_to_work(row, task_id)


def _row_to_work(row: sqlite3.Row, task_id: str) -> dict:
    cover = row["cover"] or ""
    cover_url = f"/api/tasks/{task_id}/files/{cover}" if cover else ""
    return {
        "id": row["id"],
        "task_id": row["task_id"],
        "title": row["title"],
        "prompt": row["prompt"] or "",
        "cover": cover_url,
        "cover_state": False,
        "video_path": f"/api/tasks/{task_id}/files/{row['video_path'] or 'final_video.mp4'}",
        "mode": row["mode"],
        "episode_num": row["episode_num"] or 1,
        "create_time": _format_create_time(row["created_at"]),
    }


def list_user_works(
    conn: sqlite3.Connection,
    user_id: str,
    *,
    page: int = 1,
    limit: int = 20,
    title: str = "",
) -> Tuple[List[dict], int]:
    page = max(1, page)
    limit = max(1, min(limit, 100))
    offset = (page - 1) * limit
    where = "WHERE user_id = ?"
    params: List[object] = [user_id]
    if title.strip():
        where += " AND title LIKE ?"
        params.append(f"%{title.strip()}%")

    total = conn.execute(
        f"SELECT COUNT(*) FROM user_works {where}",
        params,
    ).fetchone()[0]
    rows = conn.execute(
        f"""
        SELECT * FROM user_works
        {where}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        [*params, limit, offset],
    ).fetchall()
    items = [_row_to_work(row, row["task_id"]) for row in rows]
    return items, total


def get_user_work(
    conn: sqlite3.Connection,
    user_id: str,
    work_id: str,
) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM user_works WHERE id = ? AND user_id = ?",
        (work_id, user_id),
    ).fetchone()
    if row is None:
        return None
    return _row_to_work(row, row["task_id"])


def delete_user_work(conn: sqlite3.Connection, user_id: str, work_id: str) -> bool:
    cursor = conn.execute(
        "DELETE FROM user_works WHERE id = ? AND user_id = ?",
        (work_id, user_id),
    )
    return cursor.rowcount > 0
