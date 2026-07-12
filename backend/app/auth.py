"""用户认证模块：注册、登录、JWT 生成与校验。"""
from __future__ import annotations

import os
import time
from typing import Any, Literal

import bcrypt
import jwt
from fastapi import HTTPException, Request
from pydantic import BaseModel, Field

from .database import connect, now_ts
from .logging_config import log_event

JWT_SECRET = os.getenv("JWT_SECRET", "anti_fraud_default_secret_key_change_me")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "72"))
JWT_ALGORITHM = "HS256"

Role = Literal["user", "admin"]


# ─── Pydantic Models ─────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=30)
    password: str = Field(..., min_length=4, max_length=64)
    nickname: str = Field(default="", max_length=30)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=30)
    password: str = Field(..., min_length=1, max_length=64)


class AuthResponse(BaseModel):
    token: str
    user: "UserInfo"


class UserInfo(BaseModel):
    id: int
    username: str
    nickname: str
    role: str
    avatar: str


# ─── Database helpers ────────────────────────────────────────────

def init_users_table() -> None:
    """创建 users 表并插入默认管理员账号。"""
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                nickname TEXT NOT NULL DEFAULT '反诈小卫士',
                role TEXT NOT NULL DEFAULT 'user',
                avatar TEXT NOT NULL DEFAULT '/assets/profile-avatar.png',
                tenant_id TEXT NOT NULL DEFAULT 'default',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
    # 种子管理员
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    _ensure_user(admin_username, admin_password, role="admin", nickname="管理员")


def _ensure_user(username: str, password: str, role: str = "user", nickname: str = "") -> None:
    """如果用户不存在则创建。"""
    with connect() as conn:
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            return
        timestamp = now_ts()
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        conn.execute(
            """
            INSERT INTO users (username, password_hash, nickname, role, tenant_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (username, hashed, nickname or username, role, "default", timestamp, timestamp),
        )
    log_event("user_seeded", username=username, role=role)


# ─── Auth logic ──────────────────────────────────────────────────

def register_user(payload: RegisterRequest) -> AuthResponse:
    """注册新用户，成功后返回 token。"""
    with connect() as conn:
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (payload.username,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="用户名已存在")
        timestamp = now_ts()
        hashed = bcrypt.hashpw(payload.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        nickname = payload.nickname or payload.username
        conn.execute(
            """
            INSERT INTO users (username, password_hash, nickname, role, tenant_id, created_at, updated_at)
            VALUES (?, ?, ?, 'user', 'default', ?, ?)
            """,
            (payload.username, hashed, nickname, timestamp, timestamp),
        )
        user = conn.execute("SELECT * FROM users WHERE username = ?", (payload.username,)).fetchone()
    log_event("user_registered", username=payload.username)
    return _build_auth_response(user)


def login_user(payload: LoginRequest) -> AuthResponse:
    """验证用户名密码，成功后返回 token。"""
    with connect() as conn:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (payload.username,)).fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not bcrypt.checkpw(payload.password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    log_event("user_login", username=payload.username)
    return _build_auth_response(user)


def _build_auth_response(user) -> AuthResponse:
    """根据用户记录生成 JWT token 和用户信息。"""
    token = _generate_token(user["id"], user["username"], user["role"])
    return AuthResponse(
        token=token,
        user=UserInfo(
            id=user["id"],
            username=user["username"],
            nickname=user["nickname"],
            role=user["role"],
            avatar=user["avatar"],
        ),
    )


def _generate_token(user_id: int, username: str, role: str) -> str:
    """生成 JWT token。"""
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + JWT_EXPIRE_HOURS * 3600,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict[str, Any]:
    """验证 JWT token，返回 payload。"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的认证信息")


def get_current_user(request: Request) -> dict[str, Any] | None:
    """从请求 Authorization header 获取当前用户，未登录返回 None。"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    if not token:
        return None
    try:
        return verify_token(token)
    except HTTPException:
        return None


def require_auth(request: Request) -> dict[str, Any]:
    """要求已登录，未登录抛 401。"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def require_admin(request: Request) -> dict[str, Any]:
    """要求管理员权限，非管理员抛 403。"""
    user = require_auth(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


def get_user_info(user_id: int) -> UserInfo | None:
    """根据 user_id 获取用户信息。"""
    with connect() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return None
    return UserInfo(
        id=user["id"],
        username=user["username"],
        nickname=user["nickname"],
        role=user["role"],
        avatar=user["avatar"],
    )
