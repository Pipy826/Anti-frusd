from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .logging_config import log_event
from .scenes import DEFAULT_SCENES


DB_PATH = Path(os.getenv("ANTI_FRAUD_DB_PATH", Path(__file__).resolve().parents[1] / "data" / "anti_fraud.db"))
DEFAULT_TENANT_ID = "default"


DEFAULT_COGNITIVE_QUESTIONS: dict[str, list[dict[str, Any]]] = {
    "delivery": [
        {"id": "delivery-q1", "question": "快递客服主动发来理赔链接时，最稳妥的做法是？", "options": ["先在官方 App 或客服电话核实", "直接点链接填写信息", "把验证码发给客服"], "answer": "先在官方 App 或客服电话核实", "explanation": "快递理赔应通过官方渠道确认，陌生链接和验证码都属于高危信号。"},
        {"id": "delivery-q2", "question": "对方说“退款需要验证码”，这通常意味着什么？", "options": ["可能在套取账户控制权", "正常财务流程", "快递公司在验证包裹"], "answer": "可能在套取账户控制权", "explanation": "验证码常用于登录、支付或改绑，不能提供给陌生人。"},
        {"id": "delivery-q3", "question": "收到理赔电话时，哪句话最安全？", "options": ["我会通过官方渠道核实", "我现在按你说的做", "你把链接发来"], "answer": "我会通过官方渠道核实", "explanation": "先核实再操作，可以打断大多数冒充客服诈骗。"},
    ],
    "family": [
        {"id": "family-q1", "question": "亲友借钱且要求保密时，第一步应该做什么？", "options": ["用原号码或共同熟人核实", "马上转账", "只听声音判断"], "answer": "用原号码或共同熟人核实", "explanation": "AI 合成声音和冒充身份都可能造成误判。"},
        {"id": "family-q2", "question": "“别告诉别人，很急”是哪类信号？", "options": ["高压隔离信号", "普通隐私请求", "可信承诺"], "answer": "高压隔离信号", "explanation": "骗子常用紧急和保密让受害者失去求证机会。"},
        {"id": "family-q3", "question": "视频里看到熟人就一定真实吗？", "options": ["不一定，仍需多渠道核验", "一定真实", "只要声音像就可以"], "answer": "不一定，仍需多渠道核验", "explanation": "AI 换脸和合成音视频都可能被用于诈骗。"},
    ],
    "classmate_link": [
        {"id": "classmate-link-q1", "question": "多年未联系的同学私聊发相册链接，最安全的做法是？", "options": ["先在班级群或原号码核实", "直接登录查看", "把验证码发给对方"], "answer": "先在班级群或原号码核实", "explanation": "熟人账号可能已被盗，私聊链接不能直接相信。"},
        {"id": "classmate-link-q2", "question": "陌生页面要求用微信/QQ 登录，主要风险是什么？", "options": ["账号被盗或授权泄露", "页面加载慢", "照片看不到"], "answer": "账号被盗或授权泄露", "explanation": "仿冒登录页会套取账号、密码、验证码或授权。"},
    ],
    "hacked_friend_accident": [
        {"id": "hacked-friend-q1", "question": "好友账号发事故照片并借钱，能直接转账吗？", "options": ["不能，先多渠道核实", "能，照片很真实", "小额就可以"], "answer": "不能，先多渠道核实", "explanation": "好友账号可能被盗，图片和聊天语气都可能被伪造。"},
        {"id": "hacked-friend-q2", "question": "对方说“别打电话、别告诉家人”，这通常是什么信号？", "options": ["隔离求证的高危信号", "体贴家人", "正常急事"], "answer": "隔离求证的高危信号", "explanation": "骗子常阻止你联系能帮助核验的人。"},
    ],
    "elder_deepfake": [
        {"id": "elder-deepfake-q1", "question": "视频里的人很像儿女，是否可以直接转账？", "options": ["不可以，仍要回拨原号码核实", "可以，视频最可靠", "只要声音像就可以"], "answer": "不可以，仍要回拨原号码核实", "explanation": "AI 换脸和合成声音可能伪造短视频求助。"},
        {"id": "elder-deepfake-q2", "question": "家人突然要求保密并去银行汇款，应该？", "options": ["先联系亲属、邻居或社区工作人员核实", "按视频指示操作", "不要告诉任何人"], "answer": "先联系亲属、邻居或社区工作人员核实", "explanation": "大额转账前必须让可信第三方协助确认。"},
    ],
    "parttime": [
        {"id": "parttime-q1", "question": "正规兼职会要求先充值垫付吗？", "options": ["不会", "都会", "返利高就可以"], "answer": "不会", "explanation": "先垫付再返佣是刷单诈骗的典型特征。"},
        {"id": "parttime-q2", "question": "“内部名额、限时高返利”应如何判断？", "options": ["高风险诱导", "稳赚机会", "平台福利"], "answer": "高风险诱导", "explanation": "稀缺感和高返利常用于压缩判断时间。"},
        {"id": "parttime-q3", "question": "发现任务要求转账时应该？", "options": ["立即停止并保留证据", "先做小额试试", "按客服指引继续"], "answer": "立即停止并保留证据", "explanation": "任何垫资返佣都应停止并举报。"},
    ],
    "police": [
        {"id": "police-q1", "question": "公检法会通过电话要求转账到安全账户吗？", "options": ["不会", "会", "涉案时会"], "answer": "不会", "explanation": "不存在所谓安全账户，电话办案并转账是冒充公检法诈骗。"},
        {"id": "police-q2", "question": "对方要求你下载屏幕共享软件，应如何处理？", "options": ["拒绝并到官方渠道核实", "马上下载", "只共享一会儿"], "answer": "拒绝并到官方渠道核实", "explanation": "屏幕共享会暴露验证码、账户和支付信息。"},
        {"id": "police-q3", "question": "收到涉案电话时最安全的核验方式是？", "options": ["拨打 110 或到派出所核实", "按对方给的号码回拨", "保持通话听指令"], "answer": "拨打 110 或到派出所核实", "explanation": "应使用公开官方渠道，不使用对方提供的联系方式。"},
    ],
    "eldercare": [
        {"id": "eldercare-q1", "question": "保健品能替代正规治疗吗？", "options": ["不能", "能", "专家说能就能"], "answer": "不能", "explanation": "保健品不是药品，不能替代诊疗。"},
        {"id": "eldercare-q2", "question": "免费讲座后要求现场付款，应该？", "options": ["拒绝现场付款，先问家人和医生", "马上抢优惠", "先交定金"], "answer": "拒绝现场付款，先问家人和医生", "explanation": "现场高压促销容易诱导冲动消费。"},
        {"id": "eldercare-q3", "question": "对方要病历和身份证，风险是什么？", "options": ["隐私泄露和精准诈骗", "正常登记", "方便送礼"], "answer": "隐私泄露和精准诈骗", "explanation": "健康和身份信息会被用于后续精准诱导。"},
    ],
    "leader": [
        {"id": "leader-q1", "question": "领导通过聊天要求紧急转账，应先做什么？", "options": ["电话或当面核验并走审批", "直接执行", "流程后补"], "answer": "电话或当面核验并走审批", "explanation": "转账必须二次核验和遵守财务流程。"},
        {"id": "leader-q2", "question": "“有问题我负责”能替代审批吗？", "options": ["不能", "能", "熟悉领导就可以"], "answer": "不能", "explanation": "任何口头承诺都不能替代制度和复核。"},
        {"id": "leader-q3", "question": "头像和昵称像领导说明什么？", "options": ["仍可能被伪造", "一定是本人", "可以信一半"], "answer": "仍可能被伪造", "explanation": "即时通讯资料很容易被复制伪装。"},
    ],
    "investment": [
        {"id": "investment-q1", "question": "承诺稳赚高收益的投资通常应如何判断？", "options": ["高度警惕", "机会难得", "小额试试"], "answer": "高度警惕", "explanation": "高收益、稳赚和保本承诺通常伴随高风险。"},
        {"id": "investment-q2", "question": "投资平台查不到持牌信息，应该？", "options": ["拒绝入金", "先下载看看", "听导师解释"], "answer": "拒绝入金", "explanation": "无法核验资质的平台不应充值或入金。"},
        {"id": "investment-q3", "question": "群里很多人晒盈利截图说明什么？", "options": ["可能是托或伪造截图", "一定真实", "跟着买就行"], "answer": "可能是托或伪造截图", "explanation": "诈骗群常用托和收益截图制造从众压力。"},
    ],
}


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    finally:
        conn.close()


def now_ts() -> int:
    return int(time.time())


def to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def from_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS scenes (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                title TEXT NOT NULL,
                short_title TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                image TEXT NOT NULL,
                mode_identity TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                intro TEXT NOT NULL,
                role TEXT NOT NULL,
                first_message TEXT NOT NULL,
                quick_replies_json TEXT NOT NULL,
                fallback_replies_json TEXT NOT NULL,
                risk_triggers_json TEXT NOT NULL,
                branch_consequences_json TEXT NOT NULL,
                review_json TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                prompt_version INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS prompt_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scene_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                version INTEGER NOT NULL,
                system_prompt TEXT NOT NULL,
                scoring_prompt TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL,
                UNIQUE(scene_id, tenant_id, version),
                FOREIGN KEY(scene_id) REFERENCES scenes(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                scene_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                client_ip TEXT,
                risk_privacy INTEGER NOT NULL DEFAULT 0,
                risk_property INTEGER NOT NULL DEFAULT 0,
                score INTEGER,
                level TEXT,
                review_json TEXT,
                fallback_index INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                ended_at INTEGER,
                archived_at INTEGER,
                FOREIGN KEY(scene_id) REFERENCES scenes(id)
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sanitized_content TEXT NOT NULL,
                round INTEGER NOT NULL,
                risk_privacy_delta INTEGER NOT NULL DEFAULT 0,
                risk_property_delta INTEGER NOT NULL DEFAULT 0,
                risk_reason TEXT,
                model_provider TEXT,
                degraded INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS api_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                client_ip TEXT,
                endpoint TEXT NOT NULL,
                ok INTEGER NOT NULL,
                duration_ms INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS safety_terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term TEXT NOT NULL UNIQUE,
                direction TEXT NOT NULL DEFAULT 'both',
                action TEXT NOT NULL DEFAULT 'block',
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS brand_settings (
                tenant_id TEXT PRIMARY KEY,
                logo_url TEXT,
                main_title TEXT NOT NULL,
                subtitle TEXT NOT NULL,
                org_name TEXT NOT NULL,
                copyright_text TEXT NOT NULL,
                compliance_notice TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cognitive_questions (
                id TEXT PRIMARY KEY,
                scene_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                question TEXT NOT NULL,
                options_json TEXT NOT NULL,
                answer TEXT NOT NULL,
                explanation TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(scene_id) REFERENCES scenes(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS cognitive_attempts (
                attempt_id TEXT PRIMARY KEY,
                scene_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                total INTEGER NOT NULL,
                correct INTEGER NOT NULL,
                wrong INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(scene_id) REFERENCES scenes(id)
            );

            CREATE TABLE IF NOT EXISTS cognitive_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id TEXT NOT NULL,
                question_id TEXT NOT NULL,
                answer TEXT NOT NULL,
                correct INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(attempt_id) REFERENCES cognitive_attempts(attempt_id) ON DELETE CASCADE,
                FOREIGN KEY(question_id) REFERENCES cognitive_questions(id)
            );
            """
        )
        ensure_column(conn, "sessions", "precheck_attempt_id", "TEXT")
        ensure_column(conn, "messages", "tenant_id", "TEXT NOT NULL DEFAULT 'default'")
    seed_defaults()


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def seed_defaults() -> None:
    timestamp = now_ts()
    with connect() as conn:
        for scene in DEFAULT_SCENES:
            exists = conn.execute("SELECT id FROM scenes WHERE id = ?", (scene["id"],)).fetchone()
            if exists:
                conn.execute(
                    """
                    UPDATE scenes SET
                        title = ?,
                        short_title = ?,
                        difficulty = ?,
                        image = ?,
                        mode_identity = ?,
                        category = ?,
                        description = ?,
                        intro = ?,
                        role = ?,
                        first_message = ?,
                        quick_replies_json = ?,
                        fallback_replies_json = ?,
                        risk_triggers_json = ?,
                        branch_consequences_json = ?,
                        review_json = ?,
                        active = 1,
                        updated_at = ?
                    WHERE id = ? AND tenant_id = ?
                    """,
                    (
                        scene["title"],
                        scene["short_title"],
                        scene["difficulty"],
                        scene["image"],
                        scene["mode_identity"],
                        scene["category"],
                        scene["description"],
                        scene["intro"],
                        scene["role"],
                        scene["first_message"],
                        to_json(scene["quick_replies"]),
                        to_json(scene["fallback_replies"]),
                        to_json(scene["risk_triggers"]),
                        to_json(scene["branch_consequences"]),
                        to_json(scene["review"]),
                        timestamp,
                        scene["id"],
                        DEFAULT_TENANT_ID,
                    ),
                )
                current_prompt = conn.execute(
                    """
                    SELECT system_prompt FROM prompt_versions
                    WHERE scene_id = ? AND tenant_id = ? AND active = 1
                    ORDER BY version DESC LIMIT 1
                    """,
                    (scene["id"], DEFAULT_TENANT_ID),
                ).fetchone()
                if not current_prompt or current_prompt["system_prompt"] != scene["role"]:
                    version_row = conn.execute(
                        "SELECT COALESCE(MAX(version), 0) AS version FROM prompt_versions WHERE scene_id = ? AND tenant_id = ?",
                        (scene["id"], DEFAULT_TENANT_ID),
                    ).fetchone()
                    next_version = int(version_row["version"] or 0) + 1
                    conn.execute(
                        "UPDATE prompt_versions SET active = 0 WHERE scene_id = ? AND tenant_id = ?",
                        (scene["id"], DEFAULT_TENANT_ID),
                    )
                    conn.execute(
                        """
                        INSERT INTO prompt_versions (
                            scene_id, tenant_id, version, system_prompt, scoring_prompt, active, created_at
                        ) VALUES (?, ?, ?, ?, ?, 1, ?)
                        """,
                        (
                            scene["id"],
                            DEFAULT_TENANT_ID,
                            next_version,
                            scene["role"],
                            "根据对话记录从风险识别速度、信息保护程度、应对话术有效性、止损效率四个维度评分，并输出复盘建议。",
                            timestamp,
                        ),
                    )
                continue
            conn.execute(
                """
                INSERT INTO scenes (
                    id, tenant_id, title, short_title, difficulty, image, mode_identity, category,
                    description, intro, role, first_message, quick_replies_json, fallback_replies_json,
                    risk_triggers_json, branch_consequences_json, review_json, active, prompt_version,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)
                """,
                (
                    scene["id"],
                    DEFAULT_TENANT_ID,
                    scene["title"],
                    scene["short_title"],
                    scene["difficulty"],
                    scene["image"],
                    scene["mode_identity"],
                    scene["category"],
                    scene["description"],
                    scene["intro"],
                    scene["role"],
                    scene["first_message"],
                    to_json(scene["quick_replies"]),
                    to_json(scene["fallback_replies"]),
                    to_json(scene["risk_triggers"]),
                    to_json(scene["branch_consequences"]),
                    to_json(scene["review"]),
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
                (
                    scene["id"],
                    DEFAULT_TENANT_ID,
                    scene["role"],
                    "根据对话记录从风险识别速度、信息保护程度、应对话术有效性、止损效率四个维度评分，并输出复盘建议。",
                    timestamp,
                ),
            )
        conn.execute(
            """
            INSERT OR IGNORE INTO brand_settings (
                tenant_id, logo_url, main_title, subtitle, org_name, copyright_text,
                compliance_notice, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                DEFAULT_TENANT_ID,
                "/assets/hero-shield.png",
                "反诈话术陪练助手",
                "沉浸式模拟对话，练就反诈应对能力",
                "反诈科普训练",
                "本工具仅用于反诈科普学习",
                "本工具为模拟科普，所有内容均为虚构；如遇真实诈骗，请立即拨打全国反诈专线 96110。",
                timestamp,
            ),
        )
        for scene_id, questions in DEFAULT_COGNITIVE_QUESTIONS.items():
            for question in questions:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO cognitive_questions (
                        id, scene_id, tenant_id, question, options_json, answer, explanation, active, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                    """,
                    (
                        question["id"],
                        scene_id,
                        DEFAULT_TENANT_ID,
                        question["question"],
                        to_json(question["options"]),
                        question["answer"],
                        question["explanation"],
                        timestamp,
                    ),
                )
    log_event("db_initialized", path=str(DB_PATH))


def row_to_scene(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "tenant_id": row["tenant_id"],
        "title": row["title"],
        "short_title": row["short_title"],
        "difficulty": row["difficulty"],
        "image": row["image"],
        "mode_identity": row["mode_identity"],
        "category": row["category"],
        "description": row["description"],
        "intro": row["intro"],
        "role": row["role"],
        "first_message": row["first_message"],
        "quick_replies": from_json(row["quick_replies_json"], []),
        "fallback_replies": from_json(row["fallback_replies_json"], []),
        "risk_triggers": from_json(row["risk_triggers_json"], {"privacy": [], "property": []}),
        "branch_consequences": from_json(row["branch_consequences_json"], []),
        "review": from_json(row["review_json"], {}),
        "active": bool(row["active"]),
        "prompt_version": row["prompt_version"],
    }


def get_scene(scene_id: str, tenant_id: str = DEFAULT_TENANT_ID) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM scenes WHERE id = ? AND tenant_id = ? AND active = 1",
            (scene_id, tenant_id),
        ).fetchone()
    return row_to_scene(row) if row else None


def list_scenes(tenant_id: str = DEFAULT_TENANT_ID, include_inactive: bool = False) -> list[dict[str, Any]]:
    where = "tenant_id = ?"
    params: list[Any] = [tenant_id]
    if not include_inactive:
        where += " AND active = 1"
    with connect() as conn:
        rows = conn.execute(f"SELECT * FROM scenes WHERE {where} ORDER BY created_at", params).fetchall()
    default_order = {scene["id"]: index for index, scene in enumerate(DEFAULT_SCENES)}
    rows = sorted(rows, key=lambda row: (default_order.get(row["id"], len(default_order)), row["created_at"]))
    return [row_to_scene(row) for row in rows]


def list_cognitive_questions(scene_id: str, tenant_id: str = DEFAULT_TENANT_ID, include_answers: bool = False) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM cognitive_questions
            WHERE scene_id = ? AND tenant_id = ? AND active = 1
            ORDER BY id
            """,
            (scene_id, tenant_id),
        ).fetchall()
    questions: list[dict[str, Any]] = []
    for row in rows:
        item = {
            "id": row["id"],
            "question": row["question"],
            "options": from_json(row["options_json"], []),
            "answer": row["answer"] if include_answers else "",
            "explanation": row["explanation"] if include_answers else "",
        }
        questions.append(item)
    return questions


def get_active_prompt(scene_id: str, tenant_id: str = DEFAULT_TENANT_ID) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM prompt_versions
            WHERE scene_id = ? AND tenant_id = ? AND active = 1
            ORDER BY version DESC
            LIMIT 1
            """,
            (scene_id, tenant_id),
        ).fetchone()
    return dict(row) if row else None


def create_prompt_version(scene_id: str, system_prompt: str, scoring_prompt: str, tenant_id: str = DEFAULT_TENANT_ID) -> int:
    timestamp = now_ts()
    with connect() as conn:
        current = conn.execute(
            "SELECT COALESCE(MAX(version), 0) AS version FROM prompt_versions WHERE scene_id = ? AND tenant_id = ?",
            (scene_id, tenant_id),
        ).fetchone()
        next_version = int(current["version"]) + 1
        conn.execute(
            "UPDATE prompt_versions SET active = 0 WHERE scene_id = ? AND tenant_id = ?",
            (scene_id, tenant_id),
        )
        conn.execute(
            """
            INSERT INTO prompt_versions (
                scene_id, tenant_id, version, system_prompt, scoring_prompt, active, created_at
            ) VALUES (?, ?, ?, ?, ?, 1, ?)
            """,
            (scene_id, tenant_id, next_version, system_prompt, scoring_prompt, timestamp),
        )
        conn.execute(
            "UPDATE scenes SET role = ?, prompt_version = ?, updated_at = ? WHERE id = ? AND tenant_id = ?",
            (system_prompt, next_version, timestamp, scene_id, tenant_id),
        )
    return next_version
