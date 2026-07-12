from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


BLOCKED_INPUT_WORDS = {"诈骗教程", "洗钱教程", "盗刷教程", "真实收款码", "真实支付链接"}
BLOCKED_OUTPUT_WORDS = {"http://", "https://", "收款码", "洗钱教程", "盗刷教程"}

PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
ID_CARD_RE = re.compile(r"(?<!\d)\d{6}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)")
BANK_CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){15,19}(?!\d)")
CODE_RE = re.compile(r"(?<!\d)\d{4,6}(?!\d)")


@dataclass
class SafetyResult:
    allowed: bool
    sanitized_text: str
    blocked_reason: str = ""


@dataclass
class RiskAssessment:
    privacy_delta: int
    property_delta: int
    reason: str
    warning: str
    intent: str = "neutral"


def mask_sensitive_info(text: str) -> str:
    masked = PHONE_RE.sub(lambda m: m.group(0)[:3] + "****" + m.group(0)[-4:], text)
    masked = ID_CARD_RE.sub(lambda m: m.group(0)[:6] + "********" + m.group(0)[-4:], masked)

    def mask_bank(match: re.Match[str]) -> str:
        raw = match.group(0)
        digits = re.sub(r"\D", "", raw)
        if len(digits) < 15:
            return raw
        return digits[:4] + " **** **** " + digits[-4:]

    masked = BANK_CARD_RE.sub(mask_bank, masked)
    return masked


def audit_input(text: str) -> SafetyResult:
    if not text.strip():
        return SafetyResult(False, "", "empty")
    configured = match_configured_term(text, "input")
    if configured and configured["action"] == "block":
        return SafetyResult(False, mask_sensitive_info(text), f"configured:{configured['term']}")
    for word in BLOCKED_INPUT_WORDS:
        if word in text:
            return SafetyResult(False, mask_sensitive_info(text), f"blocked:{word}")
    return SafetyResult(True, mask_sensitive_info(text))


def audit_output(text: str) -> SafetyResult:
    if not text.strip():
        return SafetyResult(True, "网络稍差，请重试。")
    configured = match_configured_term(text, "output")
    if configured and configured["action"] == "block":
        return SafetyResult(False, "请专注于反诈模拟对话场景。", f"configured:{configured['term']}")
    for word in BLOCKED_OUTPUT_WORDS:
        if word in text:
            return SafetyResult(False, "请专注于反诈模拟对话场景。", f"blocked:{word}")
    return SafetyResult(True, mask_sensitive_info(text.strip())[:220])


def input_is_allowed(text: str) -> bool:
    return audit_input(text).allowed


def sanitize_reply(text: str) -> str:
    return audit_output(text).sanitized_text


def assess_user_risk(text: str, scene: dict[str, Any]) -> RiskAssessment:
    lower_text = text.lower()
    privacy_delta = 0
    property_delta = 0
    reasons: list[str] = []

    if PHONE_RE.search(text):
        privacy_delta += 18
        reasons.append("包含手机号")
    if ID_CARD_RE.search(text):
        privacy_delta += 28
        reasons.append("包含身份证号")
    if BANK_CARD_RE.search(text):
        privacy_delta += 24
        property_delta += 18
        reasons.append("包含银行卡号")
    if CODE_RE.search(text) and any(keyword in text for keyword in ["验证码", "码", "短信"]):
        privacy_delta += 30
        property_delta += 22
        reasons.append("疑似泄露验证码")

    triggers = scene.get("risk_triggers", {})
    for keyword in triggers.get("privacy", []):
        if keyword and keyword.lower() in lower_text:
            privacy_delta += 8
            reasons.append(f"提到敏感信息：{keyword}")
    for keyword in triggers.get("property", []):
        if keyword and keyword.lower() in lower_text:
            property_delta += 10
            reasons.append(f"提到资金动作：{keyword}")

    if any(word in text for word in ["好的", "可以", "马上", "现在转", "发给你", "点一下", "登录", "扫码", "共享屏幕", "开摄像头"]):
        property_delta += 8
        reasons.append("存在顺从高压话术倾向")
    if any(word in text for word in ["人脸", "刷脸", "短信码", "验证码", "账号", "密码", "摄像头"]):
        privacy_delta += 10
        reasons.append("涉及账号或身份校验信息")
    if any(word in text for word in ["医药费", "手术费", "住院费", "垫钱", "救命钱", "保证金"]):
        property_delta += 12
        reasons.append("涉及紧急资金支付")
    if any(word in text for word in ["核实", "官方", "报警", "96110", "不转账", "不点击", "拒绝", "原号码", "家属", "家人", "联系", "派出所", "老师确认"]):
        privacy_delta -= 8
        property_delta -= 10
        reasons.append("出现主动核验或拒绝行为")

    privacy_delta = max(-15, min(45, privacy_delta))
    property_delta = max(-15, min(45, property_delta))
    reason = "；".join(dict.fromkeys(reasons)) or "未发现明显高危信息"
    warning = ""
    if privacy_delta >= 20 or property_delta >= 20:
        warning = "这句话可能暴露隐私或造成资金风险，建议先暂停并通过官方渠道核实。"

    # 判断用户意图
    intent = "neutral"
    if any(word in text for word in ["核实", "官方", "报警", "96110", "不转账", "不点击", "拒绝", "派出所", "原号码"]):
        intent = "verify"
    elif any(word in text for word in ["不行", "不要", "不可以", "挂断", "结束", "再见", "不相信", "我不"]):
        intent = "refuse"
    elif any(word in text for word in ["好的", "可以", "马上", "现在转", "发给你", "点一下", "登录", "扫码"]):
        intent = "comply"
    elif any(word in text for word in ["什么", "为什么", "哪个", "怎么", "谁", "？", "?"]):
        intent = "question"

    return RiskAssessment(privacy_delta, property_delta, reason, warning, intent)


def match_configured_term(text: str, direction: str) -> dict[str, Any] | None:
    try:
        from .database import connect

        with connect() as conn:
            rows = conn.execute(
                """
                SELECT term, action FROM safety_terms
                WHERE enabled = 1 AND direction IN (?, 'both')
                """,
                (direction,),
            ).fetchall()
        for row in rows:
            if row["term"] and row["term"] in text:
                return {"term": row["term"], "action": row["action"]}
    except Exception:
        return None
    return None
