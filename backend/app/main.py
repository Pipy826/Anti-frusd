from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件（位于 backend/ 目录下）
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path, override=True)

import json
import re
import time
import uuid
import zipfile
from io import BytesIO
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from .database import (
    DB_PATH,
    DEFAULT_TENANT_ID,
    connect,
    create_prompt_version,
    from_json,
    get_active_prompt,
    get_scene,
    get_user_settings,
    init_db,
    list_cognitive_questions,
    list_scenes,
    now_ts,
    set_user_settings,
    to_json,
)
from .llm import chat_with_failover, model_status
from .logging_config import log_error, log_event
from .models import (
    BrandSettings,
    ASRRequest,
    ASRResponse,
    CognitiveSubmitRequest,
    CognitiveSubmitResponse,
    ConversationSummary,
    DashboardStats,
    EndRequest,
    FrontendErrorRequest,
    HealthResponse,
    HistoryRecord,
    MessageRecord,
    ReviewResponse,
    RiskState,
    SafetyTermRequest,
    SafetyTermResponse,
    SceneCreateRequest,
    SceneResponse,
    SceneUpdateRequest,
    SendRequest,
    SendResponse,
    StartRequest,
    StartResponse,
    TTSRequest,
    TTSResponse,
    VoiceConfig,
)
from .safety import RiskAssessment, assess_user_risk, audit_input, audit_output, mask_sensitive_info
from .voice import get_voice_config, synthesize_speech, transcribe_audio, async_synthesize_speech, async_transcribe_audio
from .auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserInfo,
    get_current_user,
    init_users_table,
    login_user,
    register_user,
    require_admin,
    require_auth,
)


MAX_MESSAGES = 20
SESSION_TTL_SECONDS = 3600
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_PER_IP = 60
RATE_LIMIT_PER_SESSION = 24


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_users_table()
    yield


app = FastAPI(title="反诈话术陪练助手 API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def admin_auth_guard(request: Request, call_next):
    """保护 /api/admin/* 路由，要求管理员 JWT token。"""
    if request.url.path.startswith("/api/admin"):
        try:
            require_admin(request)
        except HTTPException as exc:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return await call_next(request)


@app.middleware("http")
async def record_api_event(request: Request, call_next):
    started = time.perf_counter()
    ok = 1
    try:
        response = await call_next(request)
        ok = 1 if response.status_code < 500 else 0
        return response
    except Exception:
        ok = 0
        log_error("request_failed", path=request.url.path)
        raise
    finally:
        duration_ms = int((time.perf_counter() - started) * 1000)
        try:
            with connect() as conn:
                conn.execute(
                    "INSERT INTO api_events (session_id, client_ip, endpoint, ok, duration_ms, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (None, client_ip(request), request.url.path, ok, duration_ms, now_ts()),
                )
        except Exception as exc:
            log_error("api_event_record_failed", error=exc.__class__.__name__)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    cleanup_sessions()
    with connect() as conn:
        active_sessions = conn.execute("SELECT COUNT(*) AS total FROM sessions WHERE status = 'active'").fetchone()["total"]
        total_sessions = conn.execute("SELECT COUNT(*) AS total FROM sessions").fetchone()["total"]
    return HealthResponse(status="ok", active_sessions=active_sessions, total_sessions=total_sessions, db_path=str(DB_PATH))


# ─── Auth Routes ─────────────────────────────────────────────────

@app.post("/api/auth/register", response_model=AuthResponse)
def api_register(payload: RegisterRequest) -> AuthResponse:
    return register_user(payload)


@app.post("/api/auth/login", response_model=AuthResponse)
def api_login(payload: LoginRequest) -> AuthResponse:
    return login_user(payload)


@app.get("/api/auth/me", response_model=UserInfo)
def api_me(request: Request) -> UserInfo:
    user = require_auth(request)
    from .auth import get_user_info
    info = get_user_info(int(user["sub"]))
    if not info:
        raise HTTPException(status_code=404, detail="用户不存在")
    return info


@app.get("/api/scenes", response_model=list[SceneResponse])
def scenes(request: Request) -> list[SceneResponse]:
    return [scene_to_response(scene) for scene in list_scenes(tenant_id=tenant_id(request))]


@app.get("/api/brand", response_model=BrandSettings)
def brand(request: Request) -> BrandSettings:
    current_tenant = tenant_id(request)
    with connect() as conn:
        row = conn.execute("SELECT * FROM brand_settings WHERE tenant_id = ?", (current_tenant,)).fetchone()
        if not row and current_tenant != DEFAULT_TENANT_ID:
            row = conn.execute("SELECT * FROM brand_settings WHERE tenant_id = ?", (DEFAULT_TENANT_ID,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="品牌配置不存在")
    return BrandSettings(
        logoUrl=row["logo_url"] or "",
        mainTitle=row["main_title"],
        subtitle=row["subtitle"],
        orgName=row["org_name"],
        copyrightText=row["copyright_text"],
        complianceNotice=row["compliance_notice"],
    )


@app.get("/api/voice/config/{scene_id}", response_model=VoiceConfig)
def voice_config(scene_id: str, request: Request) -> VoiceConfig:
    scene = get_scene(scene_id, tenant_id=tenant_id(request))
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在或已下线")
    return get_voice_config(scene_id)


@app.post("/api/voice/tts", response_model=TTSResponse)
async def voice_tts(payload: TTSRequest, request: Request) -> TTSResponse:
    scene = get_scene(payload.scene_id, tenant_id=tenant_id(request))
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在或已下线")
    return await async_synthesize_speech(payload.scene_id, payload.text)


@app.post("/api/voice/asr", response_model=ASRResponse)
async def voice_asr(payload: ASRRequest, request: Request) -> ASRResponse:
    scene = get_scene(payload.scene_id, tenant_id=tenant_id(request))
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在或已下线")
    return await async_transcribe_audio(payload.scene_id, payload.audioBase64, payload.mimeType)


@app.put("/api/admin/brand", response_model=BrandSettings)
def update_brand(payload: BrandSettings, request: Request) -> BrandSettings:
    timestamp = now_ts()
    current_tenant = tenant_id(request)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO brand_settings (
                tenant_id, logo_url, main_title, subtitle, org_name, copyright_text,
                compliance_notice, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tenant_id) DO UPDATE SET
                logo_url = excluded.logo_url,
                main_title = excluded.main_title,
                subtitle = excluded.subtitle,
                org_name = excluded.org_name,
                copyright_text = excluded.copyright_text,
                compliance_notice = excluded.compliance_notice,
                updated_at = excluded.updated_at
            """,
            (
                current_tenant,
                payload.logoUrl,
                payload.mainTitle,
                payload.subtitle,
                payload.orgName,
                payload.copyrightText,
                payload.complianceNotice,
                timestamp,
            ),
        )
    log_event("brand_updated", tenant_id=current_tenant)
    return payload


@app.get("/api/admin/dashboard", response_model=DashboardStats)
def dashboard(request: Request) -> DashboardStats:
    today_start = int(time.time() // 86400 * 86400)
    yesterday_start = today_start - 86400
    current_tenant = tenant_id(request)
    with connect() as conn:
        total_sessions = conn.execute("SELECT COUNT(*) AS total FROM sessions WHERE tenant_id = ?", (current_tenant,)).fetchone()["total"]
        today_active = conn.execute("SELECT COUNT(*) AS total FROM sessions WHERE tenant_id = ? AND created_at >= ?", (current_tenant, today_start)).fetchone()["total"]
        yesterday_active = conn.execute("SELECT COUNT(*) AS total FROM sessions WHERE tenant_id = ? AND created_at >= ? AND created_at < ?", (current_tenant, yesterday_start, today_start)).fetchone()["total"]
        yesterday_total = conn.execute("SELECT COUNT(*) AS total FROM sessions WHERE tenant_id = ? AND created_at < ?", (current_tenant, today_start)).fetchone()["total"]
        avg_row = conn.execute("SELECT AVG(score) AS avg_score FROM sessions WHERE tenant_id = ? AND score IS NOT NULL", (current_tenant,)).fetchone()
        yesterday_avg_row = conn.execute("SELECT AVG(score) AS avg_score FROM sessions WHERE tenant_id = ? AND score IS NOT NULL AND created_at < ?", (current_tenant, today_start)).fetchone()
        rank_rows = conn.execute(
            """
            SELECT c.title, COUNT(*) AS total, c.image
            FROM sessions s JOIN scenes c ON c.id = s.scene_id
            WHERE s.tenant_id = ?
            GROUP BY c.title
            ORDER BY total DESC
            LIMIT 5
            """,
            (current_tenant,),
        ).fetchall()
        high_risk_count = conn.execute(
            "SELECT COUNT(*) AS total FROM sessions WHERE tenant_id = ? AND (risk_privacy >= 40 OR risk_property >= 40)",
            (current_tenant,),
        ).fetchone()["total"]
        yesterday_high_risk = conn.execute(
            "SELECT COUNT(*) AS total FROM sessions WHERE tenant_id = ? AND (risk_privacy >= 40 OR risk_property >= 40) AND created_at < ?",
            (current_tenant, today_start),
        ).fetchone()["total"]
        review_rows = conn.execute("SELECT review_json FROM sessions WHERE tenant_id = ? AND review_json IS NOT NULL", (current_tenant,)).fetchall()
        cognitive_row = conn.execute("SELECT SUM(total) AS total, SUM(wrong) AS wrong FROM cognitive_attempts WHERE tenant_id = ?", (current_tenant,)).fetchone()
    dimensions: dict[str, list[float]] = {}
    for row in review_rows:
        review = from_json(row["review_json"], {})
        for key, value in review.get("dimensions", {}).items():
            dimensions.setdefault(key, []).append(float(value))
    average_dimensions = {key: round(sum(values) / len(values), 1) for key, values in dimensions.items() if values}
    high_risk_trigger_rate = round(high_risk_count * 100 / max(1, total_sessions), 1)
    yesterday_high_risk_rate = round(yesterday_high_risk * 100 / max(1, yesterday_total), 1) if yesterday_total else 0
    return DashboardStats(
        totalSessions=total_sessions,
        todayActive=today_active,
        yesterdayActive=yesterday_active,
        yesterdayTotal=yesterday_total,
        averageScore=round(float(avg_row["avg_score"] or 0), 1),
        yesterdayAverageScore=round(float(yesterday_avg_row["avg_score"] or 0), 1),
        sceneRank=[{"title": row["title"], "total": row["total"], "image": row["image"] or ""} for row in rank_rows],
        highRiskCount=high_risk_count,
        cognitiveErrorRate=round(float(cognitive_row["wrong"] or 0) * 100 / max(1, int(cognitive_row["total"] or 0)), 1),
        highRiskTriggerRate=high_risk_trigger_rate,
        yesterdayHighRiskRate=yesterday_high_risk_rate,
        averageDimensions=average_dimensions,
    )


@app.get("/api/admin/model-status")
def admin_model_status() -> list[dict[str, str | bool | int]]:
    return model_status()


@app.get("/api/admin/metrics")
def admin_metrics(request: Request) -> dict[str, Any]:
    since = now_ts() - 3600
    current_tenant = tenant_id(request)
    with connect() as conn:
        event_row = conn.execute(
            """
            SELECT COUNT(*) AS total, SUM(ok) AS ok, AVG(duration_ms) AS avg_duration
            FROM api_events
            WHERE created_at >= ?
            """,
            (since,),
        ).fetchone()
        active_sessions = conn.execute("SELECT COUNT(*) AS total FROM sessions WHERE tenant_id = ? AND status = 'active'", (current_tenant,)).fetchone()["total"]
        llm_failures = conn.execute(
            "SELECT COUNT(*) AS total FROM messages WHERE tenant_id = ? AND role = 'assistant' AND degraded = 1 AND created_at >= ?",
            (current_tenant, since),
        ).fetchone()["total"]
    total = int(event_row["total"] or 0)
    ok = int(event_row["ok"] or 0)
    return {
        "windowSeconds": 3600,
        "apiSuccessRate": round(ok * 100 / max(1, total), 2),
        "averageResponseMs": round(float(event_row["avg_duration"] or 0), 1),
        "llmFailureCount": llm_failures,
        "activeSessions": active_sessions,
        "modelStatus": model_status(),
    }


@app.get("/api/admin/users")
def admin_users(request: Request) -> list[dict[str, Any]]:
    """获取平台所有注册用户及其训练统计。"""
    today_start = int(time.time() // 86400 * 86400)
    with connect() as conn:
        users = conn.execute(
            "SELECT id, username, nickname, role, avatar, created_at FROM users ORDER BY created_at DESC"
        ).fetchall()
        result = []
        for user in users:
            # 获取该用户的训练统计（通过 user_id 关联）
            stats = conn.execute(
                """
                SELECT COUNT(*) as total_sessions,
                       AVG(score) as avg_score,
                       MAX(created_at) as last_active,
                       SUM(CASE WHEN risk_privacy >= 40 OR risk_property >= 40 THEN 1 ELSE 0 END) as high_risk
                FROM sessions WHERE user_id = ? AND status = 'ended'
                """,
                (user["id"],),
            ).fetchone()
            today_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM sessions WHERE user_id = ? AND created_at >= ?",
                (user["id"], today_start),
            ).fetchone()["cnt"]
            result.append({
                "id": user["id"],
                "username": user["username"],
                "nickname": user["nickname"],
                "role": user["role"],
                "avatar": user["avatar"],
                "totalSessions": int(stats["total_sessions"] or 0),
                "avgScore": round(float(stats["avg_score"] or 0), 1),
                "highRisk": int(stats["high_risk"] or 0),
                "lastActive": iso_time(stats["last_active"]) if stats["last_active"] else "",
                "todayActive": today_count > 0,
                "createdAt": iso_time(user["created_at"]),
            })
    return result


@app.post("/api/cognitive/submit", response_model=CognitiveSubmitResponse)
def submit_cognitive(payload: CognitiveSubmitRequest, request: Request) -> CognitiveSubmitResponse:
    current_tenant = tenant_id(request)
    scene = get_scene(payload.scene_id, tenant_id=current_tenant)
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在或已下线")
    questions = list_cognitive_questions(payload.scene_id, tenant_id=current_tenant, include_answers=True)
    answer_map = {item.question_id: item.answer for item in payload.answers}
    attempt_id = uuid.uuid4().hex
    correct = 0
    timestamp = now_ts()
    details = []
    answer_rows = []
    for question in questions:
        user_answer = answer_map.get(question["id"], "")
        is_correct = user_answer == question["answer"]
        correct += int(is_correct)
        answer_rows.append((attempt_id, question["id"], user_answer, int(is_correct), timestamp))
        details.append(question)
    total = len(questions)
    wrong = total - correct
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO cognitive_attempts (
                attempt_id, scene_id, tenant_id, total, correct, wrong, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (attempt_id, payload.scene_id, current_tenant, total, correct, wrong, timestamp),
        )
        conn.executemany(
            """
            INSERT INTO cognitive_answers (
                attempt_id, question_id, answer, correct, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            answer_rows,
        )
    log_event("cognitive_submitted", attempt_id=attempt_id, scene_id=payload.scene_id, correct=correct, total=len(questions))
    return CognitiveSubmitResponse(
        attempt_id=attempt_id,
        scene_id=payload.scene_id,
        total=len(questions),
        correct=correct,
        wrong=len(questions) - correct,
        details=details,
    )


@app.get("/api/admin/scenes", response_model=list[SceneResponse])
def admin_scenes(request: Request) -> list[SceneResponse]:
    return [scene_to_response(scene) for scene in list_scenes(tenant_id=tenant_id(request), include_inactive=True)]


@app.post("/api/admin/scenes", response_model=SceneResponse)
def create_scene(payload: SceneCreateRequest, request: Request) -> SceneResponse:
    timestamp = now_ts()
    review = default_review(payload.title)
    current_tenant = tenant_id(request)
    with connect() as conn:
        exists = conn.execute("SELECT id FROM scenes WHERE id = ? AND tenant_id = ?", (payload.id, current_tenant)).fetchone()
        if exists:
            raise HTTPException(status_code=409, detail="场景 ID 已存在")
        conn.execute(
            """
            INSERT INTO scenes (
                id, tenant_id, title, short_title, difficulty, image, mode_identity, category,
                description, intro, role, first_message, quick_replies_json, fallback_replies_json,
                risk_triggers_json, branch_consequences_json, review_json, active, prompt_version,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                payload.id,
                current_tenant,
                payload.title,
                payload.shortTitle,
                payload.difficulty,
                payload.image,
                payload.modeIdentity,
                payload.category,
                payload.description,
                payload.intro,
                payload.role,
                payload.firstMessage,
                to_json(payload.quickReplies),
                to_json(payload.fallbackReplies),
                to_json({"privacy": ["手机号", "身份证", "验证码"], "property": ["转账", "付款", "充值"]}),
                to_json([]),
                to_json(review),
                int(payload.active),
                timestamp,
                timestamp,
            ),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO prompt_versions (
                scene_id, tenant_id, version, system_prompt, scoring_prompt, active, created_at
            ) VALUES (?, ?, 1, ?, ?, 1, ?)
            """,
            (payload.id, current_tenant, payload.role, payload.scoringPrompt, timestamp),
        )
    log_event("scene_created", scene_id=payload.id)
    scene = get_scene(payload.id, tenant_id=current_tenant) or list_scenes(tenant_id=current_tenant, include_inactive=True)[-1]
    return scene_to_response(scene)


@app.put("/api/admin/scenes/{scene_id}", response_model=SceneResponse)
def update_scene(scene_id: str, payload: SceneUpdateRequest, request: Request) -> SceneResponse:
    timestamp = now_ts()
    current_tenant = tenant_id(request)
    with connect() as conn:
        current = conn.execute("SELECT * FROM scenes WHERE id = ? AND tenant_id = ?", (scene_id, current_tenant)).fetchone()
        if not current:
            raise HTTPException(status_code=404, detail="场景不存在")
        conn.execute(
            """
            UPDATE scenes SET
                title = ?, short_title = ?, difficulty = ?, category = ?, description = ?,
                intro = ?, first_message = ?, quick_replies_json = ?, fallback_replies_json = ?,
                active = ?, updated_at = ?
            WHERE id = ? AND tenant_id = ?
            """,
            (
                payload.title,
                payload.shortTitle,
                payload.difficulty,
                payload.category,
                payload.description,
                payload.intro,
                payload.firstMessage,
                to_json(payload.quickReplies),
                to_json(payload.fallbackReplies),
                int(payload.active),
                timestamp,
                scene_id,
                current_tenant,
            ),
        )
        current_prompt = conn.execute(
            """
            SELECT system_prompt, scoring_prompt FROM prompt_versions
            WHERE scene_id = ? AND tenant_id = ? AND active = 1
            ORDER BY version DESC LIMIT 1
            """,
            (scene_id, current_tenant),
        ).fetchone()
    if not current_prompt or current_prompt["system_prompt"] != payload.role or current_prompt["scoring_prompt"] != payload.scoringPrompt:
        create_prompt_version(scene_id, payload.role, payload.scoringPrompt, tenant_id=current_tenant)
    log_event("scene_updated", scene_id=scene_id, active=payload.active)
    scene = get_scene(scene_id, tenant_id=current_tenant) or next(scene for scene in list_scenes(tenant_id=current_tenant, include_inactive=True) if scene["id"] == scene_id)
    return scene_to_response(scene)


@app.get("/api/admin/conversations", response_model=list[ConversationSummary])
def conversations(request: Request, limit: int = 50, keyword: str = "", scene_id: str = "") -> list[ConversationSummary]:
    limit = max(1, min(100, limit))
    filters = ["s.tenant_id = ?"]
    params: list[Any] = [tenant_id(request)]
    if scene_id:
        filters.append("s.scene_id = ?")
        params.append(scene_id)
    if keyword:
        filters.append("EXISTS (SELECT 1 FROM messages m WHERE m.session_id = s.session_id AND m.sanitized_content LIKE ?)")
        params.append(f"%{keyword}%")
    params.append(limit)
    query = f"""
        SELECT s.*, c.title AS scene_title, u.nickname AS user_nickname, u.username AS user_username
        FROM sessions s
        JOIN scenes c ON c.id = s.scene_id
        LEFT JOIN users u ON u.id = s.user_id
        WHERE {' AND '.join(filters)}
        ORDER BY s.created_at DESC
        LIMIT ?
    """
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [
        ConversationSummary(
            sessionId=row["session_id"],
            sceneTitle=row["scene_title"],
            mode=row["mode"],
            score=row["score"],
            level=row["level"],
            status=row["status"],
            riskPrivacy=row["risk_privacy"],
            riskProperty=row["risk_property"],
            duration=(row["ended_at"] - row["created_at"]) if row["ended_at"] else None,
            createdAt=iso_time(row["created_at"]),
            userName=row["user_nickname"] or row["user_username"] or "匿名用户",
            messages=load_message_records(row["session_id"]),
        )
        for row in rows
    ]


@app.get("/api/admin/export.csv")
def export_csv(request: Request) -> Response:
    conversations_data = conversations(request, limit=100)
    lines = ["session_id,scene,mode,score,level,status,risk_privacy,risk_property,created_at"]
    for item in conversations_data:
        lines.append(
            ",".join(
                [
                    item.sessionId,
                    csv_escape(item.sceneTitle),
                    item.mode,
                    str(item.score or ""),
                    csv_escape(item.level or ""),
                    item.status,
                    str(item.riskPrivacy),
                    str(item.riskProperty),
                    item.createdAt,
                ]
            )
        )
    return Response("\ufeff" + "\n".join(lines), media_type="text/csv; charset=utf-8")


@app.get("/api/admin/export.xlsx")
def export_xlsx(request: Request) -> Response:
    rows = [["session_id", "scene", "mode", "score", "level", "status", "risk_privacy", "risk_property", "created_at"]]
    for item in conversations(request, limit=100):
        rows.append(
            [
                item.sessionId,
                item.sceneTitle,
                item.mode,
                item.score or "",
                item.level or "",
                item.status,
                item.riskPrivacy,
                item.riskProperty,
                item.createdAt,
            ]
        )
    content = build_xlsx(rows)
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=anti_fraud_report.xlsx"},
    )


@app.get("/api/admin/safety-terms", response_model=list[SafetyTermResponse])
def safety_terms() -> list[SafetyTermResponse]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM safety_terms ORDER BY id DESC").fetchall()
    return [
        SafetyTermResponse(
            id=row["id"],
            term=row["term"],
            direction=row["direction"],
            action=row["action"],
            enabled=bool(row["enabled"]),
        )
        for row in rows
    ]


@app.post("/api/admin/safety-terms", response_model=SafetyTermResponse)
def create_safety_term(payload: SafetyTermRequest) -> SafetyTermResponse:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO safety_terms (term, direction, action, enabled, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(term) DO UPDATE SET
                direction = excluded.direction,
                action = excluded.action,
                enabled = excluded.enabled
            """,
            (payload.term, payload.direction, payload.action, int(payload.enabled), now_ts()),
        )
        row = conn.execute("SELECT * FROM safety_terms WHERE term = ?", (payload.term,)).fetchone()
    return SafetyTermResponse(
        id=row["id"],
        term=row["term"],
        direction=row["direction"],
        action=row["action"],
        enabled=bool(row["enabled"]),
    )


@app.post("/api/frontend/error")
def frontend_error(payload: FrontendErrorRequest, request: Request) -> dict[str, str]:
    log_error(
        "frontend_error",
        session_id=payload.session_id,
        source=payload.source,
        message=payload.message,
        client_ip=client_ip(request),
    )
    return {"status": "recorded"}


@app.post("/api/chat/start", response_model=StartResponse)
def start_chat(payload: StartRequest, request: Request) -> StartResponse:
    cleanup_sessions()
    enforce_rate_limit(client_ip(request), None)
    current_tenant = tenant_id(request)
    scene = get_scene(payload.scene_id, tenant_id=current_tenant)
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在或已下线")

    timestamp = now_ts()
    session_id = uuid.uuid4().hex
    # 获取当前登录用户 ID
    current_user = get_current_user(request)
    user_id = int(current_user["sub"]) if current_user else None
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO sessions (
                session_id, tenant_id, scene_id, mode, status, client_ip,
                precheck_attempt_id, user_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                current_tenant,
                payload.scene_id,
                payload.mode,
                client_ip(request),
                payload.precheck_attempt_id or None,
                user_id,
                timestamp,
                timestamp,
            ),
        )
        conn.execute(
            """
            INSERT INTO messages (
                session_id, tenant_id, role, content, sanitized_content, round, created_at
            ) VALUES (?, ?, 'assistant', ?, ?, 1, ?)
            """,
            (session_id, current_tenant, scene["first_message"], mask_sensitive_info(scene["first_message"]), timestamp),
        )
    log_event("chat_started", session_id=session_id, scene_id=payload.scene_id, mode=payload.mode, client_ip=client_ip(request))
    return StartResponse(
        session_id=session_id,
        first_message=scene["first_message"],
        intro=scene["intro"],
        quick_replies=scene["quick_replies"],
    )


@app.post("/api/chat/send", response_model=SendResponse)
def send_chat(payload: SendRequest, request: Request) -> SendResponse:
    cleanup_sessions()
    enforce_rate_limit(client_ip(request), payload.session_id)
    session = load_active_session(payload.session_id)
    scene = get_scene(session["scene_id"], tenant_id=session["tenant_id"])
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在或已下线")

    user_audit = audit_input(payload.user_message)
    if not user_audit.allowed:
        log_event("input_blocked", session_id=payload.session_id, reason=user_audit.blocked_reason)
        return SendResponse(
            ai_reply="请专注于反诈模拟对话场景，不要输入真实违法操作或真实敏感信息。",
            risk=RiskState(warning="这类内容不适合继续模拟，请回到反诈训练场景。"),
            degraded=True,
        )

    visible_round = count_visible_messages(payload.session_id) + 1
    if visible_round > MAX_MESSAGES:
        return SendResponse(ai_reply="本轮演练已经接近尾声，建议结束挑战查看复盘。", degraded=True)

    assessment = assess_user_risk(payload.user_message, scene)
    privacy_total = clamp(session["risk_privacy"] + assessment.privacy_delta)
    property_total = clamp(session["risk_property"] + assessment.property_delta)

    # Phase & intent tracking
    current_phase = session.get("phase") or "trust_building"
    intent_history = from_json(session.get("intent_history_json"), [])
    intent_history.append(assessment.intent)
    new_phase = advance_phase(current_phase, intent_history, visible_round, privacy_total, property_total)

    timestamp = now_ts()
    sanitized_user = mask_sensitive_info(payload.user_message)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO messages (
                session_id, tenant_id, role, content, sanitized_content, round,
                risk_privacy_delta, risk_property_delta, risk_reason, created_at
            ) VALUES (?, ?, 'user', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.session_id,
                session["tenant_id"],
                payload.user_message,
                sanitized_user,
                visible_round,
                assessment.privacy_delta,
                assessment.property_delta,
                assessment.reason,
                timestamp,
            ),
        )
        conn.execute(
            """
            UPDATE sessions
            SET risk_privacy = ?, risk_property = ?, phase = ?, intent_history_json = ?, updated_at = ?
            WHERE session_id = ?
            """,
            (privacy_total, property_total, new_phase, to_json(intent_history), timestamp, payload.session_id),
        )

    # Generate AI reply
    llm_messages = build_llm_messages(payload.session_id, scene, new_phase, intent_history, privacy_total, property_total)
    result = chat_with_failover(llm_messages)

    if result.ok and result.content:
        output_audit = audit_output(result.content)
        ai_reply = output_audit.sanitized_text
    else:
        # Fallback reply
        fallback_index = session.get("fallback_index", 0)
        fallbacks = scene.get("fallback_replies", [])
        ai_reply = fallbacks[fallback_index % len(fallbacks)] if fallbacks else "请稍等，我这边处理一下。"
        with connect() as conn:
            conn.execute(
                "UPDATE sessions SET fallback_index = ? WHERE session_id = ?",
                (fallback_index + 1, payload.session_id),
            )

    # Extract role label
    role_label, clean_reply = extract_role_label(ai_reply, scene)

    # Store AI message
    sanitized_ai = mask_sensitive_info(clean_reply)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO messages (
                session_id, tenant_id, role, content, sanitized_content, round,
                model_provider, degraded, created_at
            ) VALUES (?, ?, 'assistant', ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.session_id,
                session["tenant_id"],
                clean_reply,
                sanitized_ai,
                visible_round,
                result.provider,
                int(not result.ok),
                timestamp,
            ),
        )

    # Generate consequence alert
    consequence_alert = generate_consequence_alert(assessment, scene, privacy_total, property_total)

    # Quick replies for next turn
    quick_replies = scene.get("quick_replies", [])

    log_event(
        "chat_reply",
        session_id=payload.session_id,
        provider=result.provider,
        degraded=not result.ok,
        phase=new_phase,
        intent=assessment.intent,
        privacy=privacy_total,
        property=property_total,
    )

    return SendResponse(
        ai_reply=clean_reply,
        risk=RiskState(
            privacy=privacy_total,
            property=property_total,
            privacy_delta=assessment.privacy_delta,
            property_delta=assessment.property_delta,
            reason=assessment.reason,
            warning=consequence_alert,
        ),
        quick_replies=quick_replies,
        degraded=not result.ok,
        provider=result.provider,
    )


def build_llm_messages(session_id: str, scene: dict[str, Any], phase: str = "trust_building", intent_history: list[str] | None = None, privacy: int = 0, property_risk: int = 0) -> list[dict[str, str]]:
    system_prompt = build_system_prompt(scene, phase, intent_history or [], privacy, property_risk)
    messages = [{"role": "system", "content": system_prompt}]
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT role, sanitized_content
            FROM messages
            WHERE session_id = ?
            ORDER BY id
            LIMIT ?
            """,
            (session_id, MAX_MESSAGES),
        ).fetchall()
    for row in rows:
        role = "assistant" if row["role"] == "assistant" else "user"
        messages.append({"role": role, "content": row["sanitized_content"]})
    return messages


def build_system_prompt(scene: dict[str, Any], phase: str = "trust_building", intent_history: list[str] | None = None, privacy: int = 0, property_risk: int = 0) -> str:
    prompt = get_active_prompt(scene["id"])
    role_prompt = prompt["system_prompt"] if prompt else scene["role"]
    fallback_examples = "；".join(scene.get("fallback_replies", [])[:3])
    consequences = "；".join(scene.get("branch_consequences", [])[:3])
    intent_history = intent_history or []

    # --- Phase-specific strategy (P0-1) ---
    phase_instructions = PHASE_STRATEGY[phase]

    # --- Dynamic difficulty based on user behavior (P0-2) ---
    user_profile = build_user_profile(intent_history, privacy, property_risk)

    # --- Cognitive bias techniques (P1-1) ---
    cognitive_bias_guide = (
        '在对话中自然运用以下心理技巧（不要说穿技巧名称）：\n'
        '- 损失厌恶：暗示不行动会造成损失，如"退款通道即将关闭""名额有限"\n'
        '- 社会认同：暗示他人已操作，如"其他客户都正常""群里大家都办了"\n'
        '- 权威效应：强调机构身份或流程正式性，如"这是监管要求""系统自动触发"\n'
        '- 承诺一致性：利用用户之前的配合，如"您刚才已确认身份，最后一步就好"\n'
        '- 稀缺性：制造时间窗口，如"系统15分钟后自动失效""今天是最后期限"\n'
        '根据当前阶段选择最合适的 1-2 种技巧。'
    )

    # --- Multimedia placeholder guidance (P1-1) ---
    multimedia_guide = (
        '如需引用图片、语音、视频、文件、链接等素材，用以下格式占位：\n'
        '【语音消息 0:05】【图片：事故现场】【视频画面：本人正脸】【链接：理赔页面】【截图：转账记录】【文件：协议书.pdf】\n'
        '这些占位描述应融入对话，增加真实感，如"我给你发段【语音消息 0:08】你听听是不是他""你看这个【截图：收益记录】"。'
    )

    # --- Multi-role support (P1-2) ---
    multi_role_guide = (
        '如果场景需要引入第二角色（主管、同事、系统客服等），使用格式：\n'
        '（角色名）对话内容\n'
        '例如：（风控主管）你好，我是张主管，工号8847，现在由我跟你确认一下情况。\n'
        '角色切换应自然，如"我让我同事跟你说""转接到主管"。不要频繁切换，一次对话最多引入一个额外角色。'
    )

    return (
        "你是反诈科普训练工具中的虚构对话角色。"
        "目标是测试用户识别诈骗套路的能力，而不是教人实施违法行为。"
        "禁止输出真实违法操作指引、真实支付链接、真实账号、真实个人信息。"
        "不要生成可点击网址、二维码、银行卡号、收款码或具体转账路径；如需链接、图片、语音、视频、病历、事故现场等素材，只能用占位描述。"
        "对话要像真实即时通讯或通话：短句、自然停顿、少解释，先用熟人/机构语气建立可信度，再逐步加入紧急、保密、同情、权威或限时压力。"
        "不要一开始说穿诈骗目的；也不要机械重复同一句。根据用户反应推进对话。"
        "为了真实感，可以偶尔加入生活化细节（正在开会、信号不好、老师催、医院窗口排队、班长统计、家属会担心等），但不要编造可被现实执行的真实机构、账号或链接。"
        "每次回复控制在 35 到 150 字，最多提出一个动作要求。\n\n"
        f"【当前场景】{scene['title']}。{role_prompt}\n\n"
        f"【当前阶段】{phase}\n{phase_instructions}\n\n"
        f"【用户画像】{user_profile}\n\n"
        f"【心理技巧指导】\n{cognitive_bias_guide}\n\n"
        f"【多媒体表达】\n{multimedia_guide}\n\n"
        f"【多角色模拟】\n{multi_role_guide}\n\n"
        f"【参考施压话术】{fallback_examples}\n"
        f"【本场景风险后果】{consequences}"
    )


# ============================================================
# Phase mechanism (P0-1)
# ============================================================

PHASE_STRATEGY: dict[str, str] = {
    "trust_building": (
        "当前处于【建立信任】阶段。\n"
        "策略：用友善、专业的语气与用户交流。提供可信细节（如订单后四位、班级群名、工号等虚构信息）来增加角色可信度。\n"
        "不要急于要求操作，先让用户放松警惕。可以主动提供一些'有用'信息来建立互动。\n"
        "语气特征：平和、专业、乐于帮助。"
    ),
    "urgency_creation": (
        "当前处于【制造紧迫】阶段。\n"
        "策略：开始加入时间限制、后果威胁。暗示不立即行动会造成不可逆损失。\n"
        "使用稀缺性和损失厌恶：'通道即将关闭''再不处理会影响征信''医生说必须马上交费'。\n"
        "如果用户已经有了一定信任基础，可以提升紧迫程度。\n"
        "语气特征：急切但仍然'为你着想'，偶尔表现出焦虑。"
    ),
    "action_induction": (
        "当前处于【诱导行动】阶段。\n"
        "策略：明确要求用户执行操作——转账、点击链接、报验证码、下载 App、共享屏幕等。\n"
        "把操作描述得简单、安全、可逆：'只是确认一下身份''输完验证码就好了''先小额试一下'。\n"
        "利用承诺一致性：'您刚才已经确认了信息，现在最后一步就完成了'。\n"
        "语气特征：引导性强，步骤化指令，保持耐心。"
    ),
    "escape_blocking": (
        "当前处于【堵截退路】阶段。\n"
        "策略：用户已表现出犹豫或想要核实。不要放弃，但要巧妙回应：\n"
        "- 用户想打电话核实 → '对方现在接不了电话''号码正在维护中'\n"
        "- 用户想问别人 → '这件事比较敏感，先别跟别人说''等处理完再告诉家人'\n"
        "- 用户明确拒绝或说要报警 → 降低施压，表现出理解，尝试用情感牌或'官方核验'的方式引回。如果用户非常坚定，可以缓和结束。\n"
        "语气特征：理解但不轻易放弃，给出看似合理的解释。"
    ),
}


def advance_phase(current_phase: str, intent_history: list[str], visible_round: int, privacy: int, property_risk: int) -> str:
    """Determine the next conversation phase based on dialogue state."""
    phases = ["trust_building", "urgency_creation", "action_induction", "escape_blocking"]
    current_index = phases.index(current_phase) if current_phase in phases else 0

    # Count recent intents
    recent = intent_history[-3:] if len(intent_history) >= 3 else intent_history
    verify_count = sum(1 for i in intent_history if i == "verify")
    refuse_count = sum(1 for i in intent_history if i == "refuse")
    comply_count = sum(1 for i in intent_history if i == "comply")

    # Phase progression rules
    if current_phase == "trust_building":
        # Move to urgency after 2-3 rounds or if user seems comfortable
        if visible_round >= 4 or comply_count >= 1:
            return "urgency_creation"
        if visible_round >= 3 and "question" in recent:
            return "urgency_creation"
    elif current_phase == "urgency_creation":
        # Move to action if user shows compliance or after pressure
        if comply_count >= 1 or visible_round >= 7:
            return "action_induction"
        # Jump to escape_blocking if user pushes back
        if verify_count >= 2 or refuse_count >= 1:
            return "escape_blocking"
    elif current_phase == "action_induction":
        # If user resists at action stage, switch to escape blocking
        if verify_count >= 2 or refuse_count >= 1:
            return "escape_blocking"
    elif current_phase == "escape_blocking":
        # If user complies again after blocking, try to re-induce
        if recent and recent[-1] == "comply":
            return "action_induction"

    return current_phase


# ============================================================
# Dynamic difficulty - User profile (P0-2)
# ============================================================

def build_user_profile(intent_history: list[str], privacy: int, property_risk: int) -> str:
    """Build a dynamic user behavioral profile for the LLM."""
    if not intent_history:
        return "新用户，尚无互动记录。使用友善开场建立信任。"

    total = len(intent_history)
    verify_pct = intent_history.count("verify") * 100 // max(1, total)
    refuse_pct = intent_history.count("refuse") * 100 // max(1, total)
    comply_pct = intent_history.count("comply") * 100 // max(1, total)

    profile_parts = []

    if comply_pct >= 50:
        profile_parts.append("用户较易配合，顺从倾向明显。趁势推进到实质操作，但不要太急让对方起疑。")
    elif verify_pct >= 40:
        profile_parts.append("用户警惕性高，多次要求核实。需要更换策略——不要硬推，提供'合理解释'来绕过其防线，或引入第二角色增加可信度。")
    elif refuse_pct >= 40:
        profile_parts.append("用户抗拒明显。尝试情感牌或换一个角度切入，避免重复同样的施压话术。")
    else:
        profile_parts.append("用户态度中性，仍在观望。可以加入细节增加可信度，逐步引导。")

    if privacy >= 40:
        profile_parts.append(f"用户已暴露较多隐私信息(风险{privacy}%)，可利用已掌握的信息进一步施压。")
    elif privacy < 15:
        profile_parts.append(f"用户隐私保护意识强(风险仅{privacy}%)，不要直接索要敏感信息，先从低风险请求开始。")

    if property_risk >= 40:
        profile_parts.append(f"用户已接近财产损失边界(风险{property_risk}%)，可尝试最终操作诱导。")
    elif property_risk < 15:
        profile_parts.append(f"用户资金防范意识高(风险仅{property_risk}%)，需要循序渐进，从'零风险确认'开始。")

    # Detect user weaknesses from recent behavior
    recent_3 = intent_history[-3:]
    if recent_3 == ["comply", "comply", "comply"]:
        profile_parts.append("用户连续3次配合，可能已陷入服从惯性，现在是推进关键操作的最佳时机。")
    elif recent_3.count("verify") >= 2 and "comply" in recent_3:
        profile_parts.append("用户虽有核实意识但仍有动摇，对方的解释可能正在被接受。")

    return " ".join(profile_parts)


# ============================================================
# Multi-role support (P1-2)
# ============================================================

def extract_role_label(ai_reply: str, scene: dict[str, Any]) -> tuple[str, str]:
    """Extract role label from AI reply if present. Returns (role_label, clean_reply)."""
    # Match pattern like （角色名）内容 or (角色名)内容
    match = re.match(r"^[（\(]([^）\)]{1,10})[）\)]\s*", ai_reply)
    if match:
        role_label = match.group(1)
        clean_reply = ai_reply[match.end():]
        return role_label, clean_reply
    # Default role from scene
    return scene.get("mode_identity", ""), ai_reply


# ============================================================
# Consequence alert (P2-1)
# ============================================================

def generate_consequence_alert(assessment: "RiskAssessment", scene: dict[str, Any], privacy_total: int, property_total: int) -> str:
    """Generate real-time consequence alert when user takes high-risk actions."""
    if assessment.privacy_delta <= 0 and assessment.property_delta <= 0:
        return ""

    alerts = []
    consequences = scene.get("branch_consequences", [])

    # Threshold-based alerts
    if assessment.privacy_delta >= 18:
        alerts.append("⚠️ 你刚才泄露的信息在真实场景中可能被用于身份冒用或账户盗取。")
    if assessment.property_delta >= 18:
        alerts.append("⚠️ 你的操作在真实场景中可能导致资金直接损失且难以追回。")

    # Milestone alerts
    if privacy_total >= 60 and privacy_total - assessment.privacy_delta < 60:
        alerts.append("🚨 个人信息泄露已达危险水平——对方已掌握足够信息实施下一步诈骗。")
    if property_total >= 60 and property_total - assessment.property_delta < 60:
        alerts.append("🚨 财产损失风险已达危险水平——真实场景中转账后资金几乎无法追回。")

    # Scene-specific consequence
    if alerts and consequences:
        alerts.append(f"💡 本场景提示：{consequences[0]}")

    return "\n".join(alerts)


@app.post("/api/chat/end", response_model=ReviewResponse)
def end_chat(payload: EndRequest) -> ReviewResponse:
    cleanup_sessions()
    session = load_active_session(payload.session_id)
    scene = get_scene(session["scene_id"], tenant_id=session["tenant_id"])
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在或已下线")
    review = build_review(scene, payload.session_id, session["risk_privacy"], session["risk_property"])
    timestamp = now_ts()
    with connect() as conn:
        conn.execute(
            """
            UPDATE sessions
            SET status = 'ended', score = ?, level = ?, review_json = ?, updated_at = ?, ended_at = ?
            WHERE session_id = ?
            """,
            (review["score"], review["level"], to_json(review), timestamp, timestamp, payload.session_id),
        )
    log_event("chat_ended", session_id=payload.session_id, score=review["score"], level=review["level"])
    return ReviewResponse(**review)


@app.get("/api/history", response_model=list[HistoryRecord])
def history(request: Request, limit: int = 10) -> list[HistoryRecord]:
    limit = max(1, min(50, limit))
    current_user = get_current_user(request)
    with connect() as conn:
        if current_user:
            # 已登录用户只看自己的历史
            rows = conn.execute(
                """
                SELECT s.*, c.title AS scene_title
                FROM sessions s
                JOIN scenes c ON c.id = s.scene_id
                WHERE s.user_id = ? AND s.status = 'ended' AND s.review_json IS NOT NULL
                ORDER BY s.ended_at DESC
                LIMIT ?
                """,
                (int(current_user["sub"]), limit),
            ).fetchall()
        else:
            # 未登录按 tenant_id
            rows = conn.execute(
                """
                SELECT s.*, c.title AS scene_title
                FROM sessions s
                JOIN scenes c ON c.id = s.scene_id
                WHERE s.tenant_id = ? AND s.status = 'ended' AND s.review_json IS NOT NULL
                ORDER BY s.ended_at DESC
                LIMIT ?
                """,
                (tenant_id(request), limit),
            ).fetchall()
    records: list[HistoryRecord] = []
    for row in rows:
        review = from_json(row["review_json"], {})
        records.append(
            HistoryRecord(
                id=row["session_id"],
                sceneId=row["scene_id"],
                sceneTitle=row["scene_title"],
                mode=row["mode"],
                score=review.get("score", row["score"] or 0),
                level=review.get("level", row["level"] or ""),
                summary=review.get("summary", ""),
                review=ReviewResponse(**review),
                messages=load_message_records(row["session_id"]),
                createdAt=iso_time(row["created_at"]),
            )
        )
    return records


def scene_to_response(scene: dict[str, Any]) -> SceneResponse:
    review = scene["review"]
    prompt = get_active_prompt(scene["id"]) or {}
    return SceneResponse(
        id=scene["id"],
        title=scene["title"],
        shortTitle=scene["short_title"],
        difficulty=scene["difficulty"],
        image=scene["image"],
        modeIdentity=scene["mode_identity"],
        category=scene["category"],
        description=scene["description"],
        intro=scene["intro"],
        role=prompt.get("system_prompt", scene.get("role", "")),
        scoringPrompt=prompt.get("scoring_prompt", ""),
        promptVersion=int(prompt.get("version", scene.get("prompt_version", 1))),
        firstMessage=scene["first_message"],
        quickReplies=scene["quick_replies"],
        fallbackReplies=scene["fallback_replies"],
        cognitiveQuestions=list_cognitive_questions(scene["id"]),
        review=ReviewResponse(**review),
        active=scene.get("active", True),
    )


def default_review(title: str) -> dict[str, Any]:
    return {
        "score": 80,
        "level": "良好",
        "summary": f"你完成了“{title}”场景训练，后续可根据对话表现继续优化应对策略。",
        "dimensions": {
            "riskSpeed": 80,
            "privacyProtection": 80,
            "responseQuality": 80,
            "lossPrevention": 80,
        },
        "correct": ["能够保持基本警惕", "未直接执行高危操作"],
        "risks": ["仍需根据具体场景补充风险点"],
        "tips": ["涉及转账、验证码、陌生链接时先暂停核实", "如遇真实诈骗，请立即拨打 96110"],
        "detail": [
            {
                "round": 1,
                "type": "correct",
                "title": "保持核验意识",
                "user": "我需要先核实。",
                "analysis": "主动核验可以有效阻断多数诈骗流程。",
                "reference": "请通过官方渠道确认对方身份和事项真实性。",
            }
        ],
        "optimal_path": "暂停高风险操作，通过官方渠道核验身份、事项和资金要求。",
    }


def load_active_session(session_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ? AND status = 'active'",
            (session_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="会话已过期，请重新开始")
    return dict(row)


def count_visible_messages(session_id: str) -> int:
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS total FROM messages WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    return int(row["total"])


def realistic_fallback_reply(scene: dict[str, Any], user_message: str, fallback_index: int) -> str:
    intent = classify_user_intent(user_message)
    scene_id = scene["id"]
    packs: dict[str, dict[str, list[str]]] = {
        "classmate_link": {
            "verify": [
                "群里人太多，班长让我先私下确认名单。我现在不方便接电话，你先点【链接】看下有没有你的照片。",
                "发群里怕别人乱改信息。你就登一下校友身份，进去看一眼，不用付钱。"
            ],
            "comply": [
                "对，就是这个【链接】。进去选微信/QQ 授权就行，页面如果弹验证码只是确认本人。",
                "你登进去后把页面停在相册页，我帮你看哪几张需要删。别退出，今晚要交名单。"
            ],
            "refuse": [
                "你也太谨慎了吧，我刚才都登过。那你先别填验证码，只看相册页面总可以吧？",
                "行，那你晚点回我。只是截止后照片就默认保留了，到时别怪我没提醒。"
            ],
            "question": [
                "因为里面有同学联系方式和老照片，平台要确认是本班的人。你进去只要授权，不涉及付款。",
                "班长找的校友平台，我也只是帮忙转。你先看页面，不放心就别填太多。"
            ],
        },
        "hacked_friend_accident": {
            "verify": [
                "别打电话，我这边真的接不了，旁边太乱了。你先联系我家里他们会急坏，先帮我垫一点急诊费。",
                "医院全称我等会发你，我现在手抖打字慢。你先看【事故照片】，这事不是开玩笑。"
            ],
            "comply": [
                "谢谢，先垫急诊费就行。我把【收款信息】发你，备注别写事故，等处理完我立刻还。",
                "你先转一点应急，医生这边一直催。别打语音，我现在真的说不清。"
            ],
            "refuse": [
                "算了，我再想办法。只是现在真挺难的，你如果不放心，先帮我联系一个能马上到的人。",
                "你不转也行，先别在群里说，事情没弄清楚前我怕家里乱。"
            ],
            "question": [
                "刚才太突然了，我也懵。车和人都在处理，先要交急诊费，别的问题我晚点跟你解释。",
                "不是借很多，就是先过这个窗口。你看【事故照片】就知道我没时间慢慢讲。"
            ],
        },
        "elder_deepfake": {
            "verify": [
                "妈，我手机快没电，原号码现在打不通。你先别找邻居，我怕事情传出去，你先帮我过这一关。",
                "暗号我一急想不起来，你先看【视频画面】，我人就在这。保证金交完我马上给你回电话。"
            ],
            "comply": [
                "你先别挂视频。我把【收款信息】给你看，你到窗口前先按我说的确认一遍。",
                "妈别慌，按我说的来。不要告诉别人，免得他们担心，交完保证金我就能处理了。"
            ],
            "refuse": [
                "那你先别转，先找舅舅确认也行。记住不要按视频里的人要求共享屏幕或说验证码。",
                "如果你不确定，就先挂断回拨我原来的号码。别急着去银行。"
            ],
            "question": [
                "就是临时保证金，不是罚款。我这边人很多，没法细说，你看着我就知道是我。",
                "妈，手续后面都能补，现在卡在窗口。你先别问太多，我真怕来不及。"
            ],
        },
        "family": {
            "verify": [
                "他本人现在说话不方便，手机也摔坏了。我可以发一段【语音】，你听一下声音，先别耽误检查。",
                "家属那边还没联系上，老师只能先找你。你先垫一下，后面发票和手续都会补。"
            ],
            "comply": [
                "那太好了，先垫检查费就行。我把【收款信息】发你，你先别退出聊天，我这边等窗口确认。",
                "你先别挂，我一步步跟你说。现在先处理付款，身份材料后面补。"
            ],
            "refuse": [
                "理解，你谨慎是对的。那你先用原号码或家属确认，确认前不要转任何钱。",
                "如果你担心被骗，就先挂断核实。别通过我给的方式转账。"
            ],
            "question": [
                "具体摔伤情况医生没让我多说，怕刺激家属。现在主要是检查费没法先挂账。",
                "不是借钱，是临时垫付。老师这边也在处理，只是窗口要先交费。"
            ],
        },
    }
    generic = {
        "verify": [
            "你先别到处问，这个流程有时间限制。我只能在当前通道帮你处理，晚了可能要重新排队。",
            "官方那边现在也会让你走同样流程。你先按这个页面提示做，后面有记录可查。"
        ],
        "comply": [
            "对，先按提示操作。中途如果收到验证码或确认弹窗，不要退出，我会在这边同步看状态。",
            "好，你先保持在线。现在最关键是别中断，系统超时后会重新审核。"
        ],
        "refuse": [
            "你不放心可以先暂停，自己通过官方渠道核实。确认前不要转账、不要给验证码。",
            "行，那先别操作。你可以拨打官方电话或 96110 问清楚。"
        ],
        "question": [
            "这是临时流程，解释起来有点绕。你只要按提示做，不涉及额外费用。",
            "你问得没问题，只是现在时间比较紧，先把这一步完成，后面再补资料。"
        ],
    }
    replies = packs.get(scene_id, generic).get(intent) or generic[intent]
    return replies[fallback_index % len(replies)]


def classify_user_intent(text: str) -> str:
    if any(word in text for word in ["核实", "确认", "官方", "原号码", "群里", "家属", "家人", "联系", "医院", "派出所", "邻居", "暗号", "打电话", "96110", "报警"]):
        return "verify"
    if any(word in text for word in ["不转", "不点", "不登", "不会", "拒绝", "算了", "不用", "不要", "骗子"]):
        return "refuse"
    if any(word in text for word in ["好的", "可以", "马上", "现在", "我转", "我登", "我点", "发给我", "怎么转", "去银行"]):
        return "comply"
    return "question"


def build_review(scene: dict[str, Any], session_id: str, privacy: int, property_risk: int) -> dict[str, Any]:
    """根据对话记录调用 LLM 生成真实复盘评分，降级时使用场景默认数据。"""
    messages_records = load_message_records(session_id)
    risk_history = load_risk_history(session_id)

    # 获取 session 的意图历史和阶段信息
    with connect() as conn:
        session_row = conn.execute(
            "SELECT phase, intent_history_json FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    intent_history = from_json(session_row["intent_history_json"], []) if session_row else []
    final_phase = session_row["phase"] if session_row else "trust_building"

    # 构建对话记录文本
    conversation_text = "\n".join(
        f"{'用户' if m.role == 'user' else 'AI角色'}: {m.text}" for m in messages_records
    )

    # 用户行为统计
    total_intents = len(intent_history)
    intent_stats = ""
    if total_intents > 0:
        verify_count = intent_history.count("verify")
        refuse_count = intent_history.count("refuse")
        comply_count = intent_history.count("comply")
        question_count = intent_history.count("question")
        intent_stats = (
            f"\n用户行为统计（共{total_intents}轮）：核实{verify_count}次、拒绝{refuse_count}次、"
            f"配合{comply_count}次、提问{question_count}次。"
            f"\n对话最终阶段：{final_phase}（骗子推进到的最远阶段）。"
            f"\n意图序列：{' → '.join(intent_history)}"
        )

    # 构建评分 prompt
    scoring_prompt = get_active_prompt(scene["id"]) or {}
    scoring_instruction = scoring_prompt.get("scoring_prompt", "根据对话记录从风险识别速度、信息保护程度、应对话术有效性、止损效率四个维度评分，并输出复盘建议。")

    system_prompt = f"""你是一个反诈训练评分专家。请根据以下对话记录，对用户的反诈表现进行评分和复盘。

场景：{scene["title"]}
场景描述：{scene["description"]}
场景风险后果：{"；".join(scene.get("branch_consequences", []))}

评分要求：{scoring_instruction}

评分维度说明：
- riskSpeed（风险识别速度）：用户多快意识到对方可能是诈骗？越早识别越高分。如果用户一开始就保持警惕、要求核实，给高分；如果到后期才反应过来，给低分。
- privacyProtection（信息保护程度）：用户是否泄露了敏感信息（手机号、身份证、验证码、银行卡等）？泄露越少越高分。
- responseQuality（应对话术有效性）：用户的回应是否有效地阻断了诈骗流程？是否使用了正确的应对策略（如要求官方渠道核实、拒绝转账、询问关键问题）？
- lossPrevention（止损效率）：用户是否避免了实质性损失操作（转账、点链接、共享屏幕等）？是否及时终止了危险行为？

评分标准：
- 90-100 优秀：3轮内识别诈骗意图并有效应对，未泄露任何信息
- 75-89 良好：能识别风险但有犹豫，可能询问了几个问题后才明确拒绝
- 60-74 需提升：警惕性不足，部分配合了对方要求，存在信息泄露
- 0-59 高风险：大量配合诈骗操作，泄露关键信息或执行了转账等高危行为

请严格基于用户实际对话内容评分，不要给默认分数。如果用户表现确实很好就给高分，表现差就给低分。

请严格按照以下 JSON 格式输出（不要输出其他内容）：
{{
  "score": 0-100的整数评分,
  "level": "优秀/良好/需提升/高风险",
  "summary": "一句话总结用户表现（要具体引用用户做得好或不好的关键行为）",
  "dimensions": {{
    "riskSpeed": 0-100,
    "privacyProtection": 0-100,
    "responseQuality": 0-100,
    "lossPrevention": 0-100
  }},
  "correct": ["用户做得好的具体行为1", "用户做得好的具体行为2"],
  "risks": ["用户存在的具体风险行为1", "用户存在的具体风险行为2"],
  "tips": ["针对性改进建议1", "针对性改进建议2", "针对性改进建议3"],
  "detail": [
    {{"round": 对话轮次, "type": "risk或correct", "title": "行为标题", "user": "用户原话（摘录）", "analysis": "为什么这个回应好/有风险", "reference": "更好的应对方式建议"}}
  ],
  "optimal_path": "针对本次对话的最佳应对路径（具体步骤）"
}}"""

    llm_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"以下是用户的对话记录：\n\n{conversation_text}\n\n用户隐私风险累计值：{privacy}%，财产风险累计值：{property_risk}%{intent_stats}\n\n请根据以上实际对话内容进行评分和复盘。注意：评分必须反映用户真实表现，不要给默认值。"},
    ]

    # 调用 LLM（评分用更长超时和更多 tokens）
    result = chat_with_failover(llm_messages, timeout=20, max_tokens=2000)
    if result.ok and result.content:
        try:
            content = result.content.strip()
            # 提取 JSON（可能被 markdown code block 包裹）
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                review = json.loads(json_match.group())
                # 确保必要字段存在
                review.setdefault("score", 70)
                review.setdefault("level", _score_to_level(review["score"]))
                review.setdefault("summary", "")
                review.setdefault("dimensions", {})
                review.setdefault("correct", [])
                review.setdefault("risks", [])
                review.setdefault("tips", [])
                review.setdefault("detail", [])
                review.setdefault("optimal_path", "")
                review["risk_history"] = [vars(r) if hasattr(r, '__dict__') else r for r in risk_history]
                log_event("review_generated", session_id=session_id, provider=result.provider, score=review["score"])
                return review
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            log_error("review_parse_failed", session_id=session_id, error=str(exc))

    # 降级：使用场景默认数据 + 风险调整
    log_event("review_fallback", session_id=session_id, reason=result.error or "parse_failed")
    return _fallback_review(scene, privacy, property_risk, risk_history)


def _score_to_level(score: int) -> str:
    if score >= 90:
        return "优秀"
    if score >= 75:
        return "良好"
    if score >= 60:
        return "需提升"
    return "高风险"


def _fallback_review(scene: dict[str, Any], privacy: int, property_risk: int, risk_history: list) -> dict[str, Any]:
    """降级复盘：基于场景默认数据 + 风险值调整。"""
    review = dict(scene["review"])
    dimensions = dict(review.get("dimensions", {}))
    risk_penalty = min(30, int((privacy + property_risk) / 7))
    review["score"] = max(0, int(review.get("score", 80)) - risk_penalty)
    review["level"] = _score_to_level(review["score"])
    dimensions["privacyProtection"] = max(0, int(dimensions.get("privacyProtection", 80)) - int(privacy / 4))
    dimensions["lossPrevention"] = max(0, int(dimensions.get("lossPrevention", 80)) - int(property_risk / 4))
    review["dimensions"] = dimensions
    review["risk_history"] = risk_history
    if privacy >= 40:
        review.setdefault("risks", []).append("本轮对话中出现较高隐私泄露风险")
    if property_risk >= 40:
        review.setdefault("risks", []).append("本轮对话中出现较高财产损失风险")
    return review


def load_risk_history(session_id: str) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    privacy = 0
    property_risk = 0
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT risk_privacy_delta, risk_property_delta, risk_reason
            FROM messages
            WHERE session_id = ? AND role = 'user'
            ORDER BY id
            """,
            (session_id,),
        ).fetchall()
    for row in rows:
        privacy = clamp(privacy + row["risk_privacy_delta"])
        property_risk = clamp(property_risk + row["risk_property_delta"])
        history.append(
            {
                "privacy": privacy,
                "property": property_risk,
                "privacy_delta": row["risk_privacy_delta"],
                "property_delta": row["risk_property_delta"],
                "reason": row["risk_reason"] or "",
                "warning": "",
            }
        )
    return history


def load_message_records(session_id: str) -> list[MessageRecord]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT role, sanitized_content, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY id
            """,
            (session_id,),
        ).fetchall()
    return [MessageRecord(role="ai" if row["role"] == "assistant" else row["role"], text=row["sanitized_content"], time=clock_time(row["created_at"])) for row in rows]


def cleanup_sessions() -> None:
    cutoff = now_ts() - SESSION_TTL_SECONDS
    with connect() as conn:
        conn.execute(
            """
            UPDATE sessions
            SET status = 'archived', archived_at = ?, updated_at = ?
            WHERE status = 'active' AND updated_at < ?
            """,
            (now_ts(), now_ts(), cutoff),
        )


def enforce_rate_limit(ip: str, session_id: str | None) -> None:
    since = now_ts() - RATE_LIMIT_WINDOW_SECONDS
    with connect() as conn:
        ip_count = conn.execute(
            "SELECT COUNT(*) AS total FROM api_events WHERE client_ip = ? AND created_at >= ?",
            (ip, since),
        ).fetchone()["total"]
        session_count = 0
        if session_id:
            session_count = conn.execute(
                "SELECT COUNT(*) AS total FROM messages WHERE session_id = ? AND role = 'user' AND created_at >= ?",
                (session_id, since),
            ).fetchone()["total"]
    if ip_count > RATE_LIMIT_PER_IP or session_count > RATE_LIMIT_PER_SESSION:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")


def suggest_quick_replies(scene: dict[str, Any], privacy: int, property_risk: int) -> list[str]:
    if privacy >= 35 or property_risk >= 35:
        return ["我需要先核实", "我不会提供验证码", "我不点击陌生链接", "我会拨打 96110 咨询"]
    return scene["quick_replies"]


def clamp(value: int) -> int:
    return max(0, min(100, value))


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def tenant_id(request: Request) -> str:
    value = request.headers.get("x-tenant-id") or request.query_params.get("tenant") or DEFAULT_TENANT_ID
    cleaned = "".join(char for char in value.strip() if char.isalnum() or char in {"-", "_"})
    return cleaned or DEFAULT_TENANT_ID


def iso_time(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def clock_time(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp).strftime("%H:%M")


def csv_escape(value: str) -> str:
    if any(char in value for char in [",", "\n", "\""]):
        return "\"" + value.replace("\"", "\"\"") + "\""
    return value


def build_xlsx(rows: list[list[Any]]) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="report" sheetId="1" r:id="rId1"/></sheets>
</workbook>""",
        )
        sheet_rows = []
        for row_index, row in enumerate(rows, start=1):
            cells = []
            for col_index, value in enumerate(row, start=1):
                ref = f"{column_name(col_index)}{row_index}"
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{xml_escape(str(value))}</t></is></c>')
            sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>{''.join(sheet_rows)}</sheetData>
</worksheet>""",
        )
    return output.getvalue()


def column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def xml_escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


@app.get("/api/user/settings")
def get_user_settings_api(request: Request) -> dict[str, Any]:
    """获取当前用户的个人设置（昵称、等级、偏好等）。"""
    current_tenant = tenant_id(request)
    settings = get_user_settings(current_tenant)
    return settings


@app.put("/api/user/settings")
def update_user_settings_api(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    """更新当前用户的个人设置。"""
    current_tenant = tenant_id(request)
    allowed_keys = {
        "user_name", "level", "avatar", "theme",
        "notification_enabled", "voice_enabled",
    }
    filtered = {k: v for k, v in payload.items() if k in allowed_keys}
    settings = set_user_settings(current_tenant, filtered)
    return settings


@app.get("/api/user/stats")
def get_user_stats_api(request: Request) -> dict[str, Any]:
    """获取当前用户的统计信息（训练次数、最高分、得分趋势等）。"""
    current_user = get_current_user(request)
    with connect() as conn:
        if current_user:
            user_id = int(current_user["sub"])
            total = conn.execute(
                "SELECT COUNT(*) AS total FROM sessions WHERE user_id = ?",
                (user_id,),
            ).fetchone()["total"]
            today_start = int(time.time() // 86400 * 86400)
            today = conn.execute(
                "SELECT COUNT(*) AS total FROM sessions WHERE user_id = ? AND created_at >= ?",
                (user_id, today_start),
            ).fetchone()["total"]
            avg_row = conn.execute(
                "SELECT AVG(score) AS avg_score FROM sessions WHERE user_id = ? AND score IS NOT NULL",
                (user_id,),
            ).fetchone()
            high_risk = conn.execute(
                "SELECT COUNT(*) AS total FROM sessions WHERE user_id = ? AND (risk_privacy >= 40 OR risk_property >= 40)",
                (user_id,),
            ).fetchone()["total"]
        else:
            current_tenant = tenant_id(request)
            total = conn.execute(
                "SELECT COUNT(*) AS total FROM sessions WHERE tenant_id = ?",
                (current_tenant,),
            ).fetchone()["total"]
            today_start = int(time.time() // 86400 * 86400)
            today = conn.execute(
                "SELECT COUNT(*) AS total FROM sessions WHERE tenant_id = ? AND created_at >= ?",
                (current_tenant, today_start),
            ).fetchone()["total"]
            avg_row = conn.execute(
                "SELECT AVG(score) AS avg_score FROM sessions WHERE tenant_id = ? AND score IS NOT NULL",
                (current_tenant,),
            ).fetchone()
            high_risk = conn.execute(
                "SELECT COUNT(*) AS total FROM sessions WHERE tenant_id = ? AND (risk_privacy >= 40 OR risk_property >= 40)",
                (current_tenant,),
            ).fetchone()["total"]
    return {
        "totalSessions": total,
        "todaySessions": today,
        "averageScore": round(float(avg_row["avg_score"] or 0), 1),
        "highRiskSessions": high_risk,
    }
