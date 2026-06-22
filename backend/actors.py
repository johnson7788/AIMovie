"""Persist user-created actors (演员库)."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional


_STATUS_ENUM = {
    "initializing": {"value": "initializing", "label": "待初始化", "props": {"type": "info"}},
    "pending": {"value": "pending", "label": "生成中", "props": {"type": "warning"}},
    "success": {"value": "success", "label": "已完成", "props": {"type": "success"}},
    "error": {"value": "error", "label": "生成失败", "props": {"type": "danger"}},
}


def _status_enum(status: Optional[str]) -> dict:
    return _STATUS_ENUM.get(status or "initializing", _STATUS_ENUM["initializing"])


def init_actor_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS actors (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            drama_id TEXT,
            episode_id TEXT,
            scope TEXT NOT NULL DEFAULT 'personal',
            name TEXT,
            headimg TEXT,
            three_view_image TEXT,
            reference_headimg TEXT,
            species_type INTEGER,
            gender INTEGER,
            age INTEGER,
            remarks TEXT,
            image_model_id TEXT,
            three_view_model_id TEXT,
            voice_channel TEXT,
            voice_id TEXT,
            voice_name TEXT,
            voice_model_id TEXT,
            status TEXT NOT NULL DEFAULT 'initializing',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_actors_user_id ON actors(user_id)"
    )


def _to_int(value) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _row_to_actor(row: sqlite3.Row, current_user_id: str) -> dict:
    is_edit = row["scope"] == "personal" and row["user_id"] == current_user_id
    return {
        "id": row["id"],
        "drama_id": row["drama_id"] or "",
        "episode_id": row["episode_id"] or "",
        "name": row["name"] or "",
        "headimg": row["headimg"] or "",
        "three_view_image": row["three_view_image"] or "",
        "reference_headimg": row["reference_headimg"] or "",
        "species_type": row["species_type"],
        "gender": row["gender"],
        "age": row["age"],
        "remarks": row["remarks"] or "",
        "image_model_id": row["image_model_id"] or "",
        "three_view_model_id": row["three_view_model_id"] or "",
        "voice_channel": row["voice_channel"],
        "voice_id": row["voice_id"],
        "voice_name": row["voice_name"],
        "voice_model_id": row["voice_model_id"],
        "status": row["status"],
        "status_enum": _status_enum(row["status"]),
        "is_edit": is_edit,
    }


def list_actors(
    conn: sqlite3.Connection,
    user_id: str,
    *,
    type: str = "all",
    name: str = "",
    species_type=None,
    gender=None,
    age=None,
    drama_id: str = "",
    episode_id: str = "",
) -> List[dict]:
    where: List[str] = []
    params: List[object] = []

    if type == "personal":
        where.append("scope = 'personal' AND user_id = ?")
        params.append(user_id)
    elif type == "public":
        where.append("scope = 'public'")
    else:  # all
        where.append("(scope = 'public' OR user_id = ?)")
        params.append(user_id)

    if name and name.strip():
        where.append("name LIKE ?")
        params.append(f"%{name.strip()}%")
    for column, value in (
        ("species_type", _to_int(species_type)),
        ("gender", _to_int(gender)),
        ("age", _to_int(age)),
    ):
        if value is not None:
            where.append(f"{column} = ?")
            params.append(value)
    if drama_id:
        where.append("drama_id = ?")
        params.append(drama_id)
    if episode_id:
        where.append("episode_id = ?")
        params.append(episode_id)

    clause = " AND ".join(where)
    rows = conn.execute(
        f"SELECT * FROM actors WHERE {clause} ORDER BY created_at DESC",
        params,
    ).fetchall()
    return [_row_to_actor(row, user_id) for row in rows]


def get_actor(conn: sqlite3.Connection, user_id: str, actor_id: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM actors WHERE id = ?", (actor_id,)
    ).fetchone()
    if row is None:
        return None
    return _row_to_actor(row, user_id)


def upsert_actor(conn: sqlite3.Connection, user_id: str, data: dict) -> dict:
    actor_id = (data.get("id") or "").strip()
    fields = {
        "drama_id": (data.get("drama_id") or "") or None,
        "episode_id": (data.get("episode_id") or "") or None,
        "name": data.get("name") or "",
        "headimg": data.get("headimg") or "",
        "three_view_image": data.get("three_view_image") or "",
        "reference_headimg": data.get("reference_headimg") or "",
        "species_type": _to_int(data.get("species_type")),
        "gender": _to_int(data.get("gender")),
        "age": _to_int(data.get("age")),
        "remarks": data.get("remarks") or "",
        "image_model_id": data.get("image_model_id") or "",
        "three_view_model_id": data.get("three_view_model_id") or "",
        "voice_channel": data.get("voice_channel"),
        "voice_id": data.get("voice_id"),
        "voice_name": data.get("voice_name"),
        "voice_model_id": data.get("voice_model_id"),
    }
    now = datetime.utcnow().isoformat(sep=" ", timespec="seconds")

    existing = None
    if actor_id:
        existing = conn.execute(
            "SELECT id FROM actors WHERE id = ? AND user_id = ?",
            (actor_id, user_id),
        ).fetchone()

    if existing is not None:
        set_clause = ", ".join(f"{key} = ?" for key in fields)
        conn.execute(
            f"UPDATE actors SET {set_clause}, updated_at = ? WHERE id = ? AND user_id = ?",
            [*fields.values(), now, actor_id, user_id],
        )
    else:
        actor_id = str(uuid.uuid4())
        columns = ["id", "user_id", "scope", "status", *fields.keys()]
        placeholders = ", ".join("?" for _ in columns)
        conn.execute(
            f"INSERT INTO actors ({', '.join(columns)}) VALUES ({placeholders})",
            [actor_id, user_id, "personal", "initializing", *fields.values()],
        )

    row = conn.execute("SELECT * FROM actors WHERE id = ?", (actor_id,)).fetchone()
    return _row_to_actor(row, user_id)


def set_actor_status(
    conn: sqlite3.Connection, user_id: str, actor_id: str, status: str
) -> None:
    now = datetime.utcnow().isoformat(sep=" ", timespec="seconds")
    conn.execute(
        "UPDATE actors SET status = ?, updated_at = ? WHERE id = ? AND user_id = ?",
        (status, now, actor_id, user_id),
    )


def update_actor_images(
    conn: sqlite3.Connection,
    user_id: str,
    actor_id: str,
    *,
    status: str,
    headimg: Optional[str] = None,
    three_view_image: Optional[str] = None,
) -> Optional[dict]:
    sets = ["status = ?"]
    params: List[object] = [status]
    if headimg is not None:
        sets.append("headimg = ?")
        params.append(headimg)
    if three_view_image is not None:
        sets.append("three_view_image = ?")
        params.append(three_view_image)
    sets.append("updated_at = ?")
    params.append(datetime.utcnow().isoformat(sep=" ", timespec="seconds"))
    params.extend([actor_id, user_id])
    conn.execute(
        f"UPDATE actors SET {', '.join(sets)} WHERE id = ? AND user_id = ?",
        params,
    )
    return get_actor(conn, user_id, actor_id)


def delete_actor(conn: sqlite3.Connection, user_id: str, actor_id: str) -> bool:
    cursor = conn.execute(
        "DELETE FROM actors WHERE id = ? AND user_id = ? AND scope = 'personal'",
        (actor_id, user_id),
    )
    return cursor.rowcount > 0
