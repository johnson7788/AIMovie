"""Username/password authentication backed by SQLite."""

from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Optional

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{4,30}$")
PASSWORD_MIN_LEN = 5
PASSWORD_MAX_LEN = 30
TOKEN_TTL_DAYS = 30


def init_auth_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            nickname TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)"
    )


def _hash_password(password: str, salt: Optional[str] = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    return secrets.compare_digest(_hash_password(password, salt), stored)


def validate_username(username: str) -> Optional[str]:
    username = (username or "").strip()
    if not USERNAME_PATTERN.match(username):
        return "用户名需为4-30位字母、数字或下划线"
    return None


def validate_password(password: str) -> Optional[str]:
    if not password or len(password) < PASSWORD_MIN_LEN or len(password) > PASSWORD_MAX_LEN:
        return f"密码长度需为{PASSWORD_MIN_LEN}-{PASSWORD_MAX_LEN}位"
    return None


def _row_to_user(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "username": row["username"],
        "nickname": row["nickname"],
        "mobile": "",
        "avatar": "",
        "is_guest": False,
    }


def _create_session(conn: sqlite3.Connection, user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=TOKEN_TTL_DAYS)
    conn.execute(
        "INSERT INTO user_sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, expires_at.isoformat(sep=" ", timespec="seconds")),
    )
    return token


def register_user(conn: sqlite3.Connection, username: str, password: str) -> tuple[dict, str]:
    username = username.strip()
    username_error = validate_username(username)
    if username_error:
        raise ValueError(username_error)
    password_error = validate_password(password)
    if password_error:
        raise ValueError(password_error)

    existing = conn.execute(
        "SELECT id FROM users WHERE username = ?", (username,)
    ).fetchone()
    if existing:
        raise ValueError("用户名已存在")

    user_id = str(uuid.uuid4())
    nickname = username
    password_hash = _hash_password(password)
    conn.execute(
        "INSERT INTO users (id, username, password_hash, nickname) VALUES (?, ?, ?, ?)",
        (user_id, username, password_hash, nickname),
    )
    token = _create_session(conn, user_id)
    user = {
        "id": user_id,
        "username": username,
        "nickname": nickname,
        "mobile": "",
        "avatar": "",
        "is_guest": False,
        "token": token,
    }
    return user, token


def login_user(conn: sqlite3.Connection, username: str, password: str) -> tuple[dict, str]:
    username = (username or "").strip()
    if not username or not password:
        raise ValueError("请输入账号和密码")

    row = conn.execute(
        "SELECT id, username, nickname, password_hash FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if row is None or not _verify_password(password, row["password_hash"]):
        raise ValueError("账号或密码错误")

    token = _create_session(conn, row["id"])
    user = _row_to_user(row)
    user["token"] = token
    return user, token


def get_user_by_token(conn: sqlite3.Connection, token: Optional[str]) -> Optional[dict]:
    if not token:
        return None
    row = conn.execute(
        """
        SELECT u.id, u.username, u.nickname, s.expires_at
        FROM user_sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token = ?
        """,
        (token,),
    ).fetchone()
    if row is None:
        return None

    expires_at = datetime.fromisoformat(row["expires_at"])
    if expires_at < datetime.utcnow():
        conn.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
        return None

    user = _row_to_user(row)
    user["token"] = token
    return user


def revoke_token(conn: sqlite3.Connection, token: Optional[str]) -> None:
    if token:
        conn.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
