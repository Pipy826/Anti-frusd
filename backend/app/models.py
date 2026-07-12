from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Mode = Literal["text", "phone", "video"]


class StartRequest(BaseModel):
    scene_id: str = Field(..., min_length=1)
    mode: Mode
    precheck_attempt_id: str = ""


class RiskState(BaseModel):
    privacy: int = 0
    property: int = 0
    privacy_delta: int = 0
    property_delta: int = 0
    reason: str = ""
    warning: str = ""


class StartResponse(BaseModel):
    session_id: str
    first_message: str
    intro: str = ""
    risk: RiskState = Field(default_factory=RiskState)
    quick_replies: list[str] = Field(default_factory=list)


class SendRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    user_message: str = Field(..., min_length=1, max_length=500)


class SendResponse(BaseModel):
    ai_reply: str
    risk: RiskState = Field(default_factory=RiskState)
    quick_replies: list[str] = Field(default_factory=list)
    degraded: bool = False
    provider: str = "fallback"
    phase: str = "trust_building"
    consequence_alert: str = ""
    role_label: str = ""


class EndRequest(BaseModel):
    session_id: str = Field(..., min_length=1)


class ReviewDetail(BaseModel):
    round: int
    type: Literal["risk", "correct"]
    title: str
    user: str
    analysis: str
    reference: str = ""


class ReviewResponse(BaseModel):
    score: int
    level: str
    summary: str
    dimensions: dict[str, int] = Field(default_factory=dict)
    correct: list[str]
    risks: list[str]
    tips: list[str]
    detail: list[ReviewDetail]
    optimal_path: str = ""
    risk_history: list[RiskState] = Field(default_factory=list)


class SceneResponse(BaseModel):
    id: str
    title: str
    shortTitle: str
    difficulty: str
    image: str
    modeIdentity: str
    category: str
    description: str
    intro: str
    role: str = ""
    scoringPrompt: str = ""
    promptVersion: int = 1
    firstMessage: str
    quickReplies: list[str]
    fallbackReplies: list[str]
    cognitiveQuestions: list["CognitiveQuestion"] = Field(default_factory=list)
    review: ReviewResponse
    active: bool = True


class CognitiveQuestion(BaseModel):
    id: str
    question: str
    options: list[str]
    answer: str = ""
    explanation: str = ""


class CognitiveAnswer(BaseModel):
    question_id: str
    answer: str


class CognitiveSubmitRequest(BaseModel):
    scene_id: str = Field(..., min_length=1)
    answers: list[CognitiveAnswer] = Field(default_factory=list)


class CognitiveSubmitResponse(BaseModel):
    attempt_id: str
    scene_id: str
    total: int
    correct: int
    wrong: int
    details: list[CognitiveQuestion]


class MessageRecord(BaseModel):
    role: str
    text: str
    time: str = ""


class HistoryRecord(BaseModel):
    id: str
    sceneId: str
    sceneTitle: str
    mode: Mode
    score: int
    level: str
    summary: str
    review: ReviewResponse
    messages: list[MessageRecord]
    createdAt: str


class HealthResponse(BaseModel):
    status: str
    active_sessions: int
    total_sessions: int
    db_path: str


class BrandSettings(BaseModel):
    logoUrl: str = ""
    mainTitle: str
    subtitle: str
    orgName: str
    copyrightText: str
    complianceNotice: str


class FrontendErrorRequest(BaseModel):
    message: str = Field(..., max_length=1000)
    source: str = Field(default="frontend", max_length=100)
    stack: str = Field(default="", max_length=4000)
    session_id: str = ""


class SceneUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=80)
    shortTitle: str = Field(..., min_length=1, max_length=20)
    difficulty: str = Field(..., min_length=1, max_length=8)
    category: str = Field(default="青年专区", max_length=20)
    description: str = Field(..., min_length=1, max_length=300)
    intro: str = Field(..., min_length=1, max_length=500)
    role: str = Field(default="你正在扮演虚构反诈训练角色。", min_length=1, max_length=1000)
    scoringPrompt: str = Field(default="根据对话记录从四个维度评分。", min_length=1, max_length=1000)
    firstMessage: str = Field(..., min_length=1, max_length=300)
    quickReplies: list[str] = Field(default_factory=list)
    fallbackReplies: list[str] = Field(default_factory=list)
    active: bool = True


class SceneCreateRequest(SceneUpdateRequest):
    id: str = Field(..., min_length=2, max_length=40)
    image: str = "/assets/hero-shield.png"
    modeIdentity: str = "训练角色"
    role: str = "你正在扮演虚构反诈训练角色。"


class DashboardStats(BaseModel):
    totalSessions: int
    todayActive: int
    yesterdayActive: int = 0
    yesterdayTotal: int = 0
    averageScore: float
    yesterdayAverageScore: float = 0
    sceneRank: list[dict[str, int | str]]
    highRiskCount: int
    cognitiveErrorRate: float = 0
    highRiskTriggerRate: float = 0
    yesterdayHighRiskRate: float = 0
    averageDimensions: dict[str, float]


class ConversationSummary(BaseModel):
    sessionId: str
    sceneTitle: str
    mode: Mode
    score: int | None = None
    level: str | None = None
    status: str
    riskPrivacy: int
    riskProperty: int
    duration: int | None = None
    createdAt: str
    userName: str = "匿名用户"
    messages: list[MessageRecord] = Field(default_factory=list)


class SafetyTermRequest(BaseModel):
    term: str = Field(..., min_length=1, max_length=80)
    direction: Literal["input", "output", "both"] = "both"
    action: Literal["block", "warn"] = "block"
    enabled: bool = True


class SafetyTermResponse(SafetyTermRequest):
    id: int


class VoiceConfig(BaseModel):
    sceneId: str
    ttsProvider: str
    ttsFallback: str
    asrProvider: str
    asrFallback: str
    voiceName: str
    voiceGender: Literal["male", "female", "neutral"] = "neutral"
    rate: float = 0.95
    phoneNumber: str
    location: str


class TTSRequest(BaseModel):
    scene_id: str
    text: str = Field(..., min_length=1, max_length=1000)


class TTSResponse(BaseModel):
    provider: str
    voiceName: str
    audioBase64: str = ""
    mimeType: str = "audio/mpeg"
    degraded: bool = False
    fallback: str = "browser"
    error: str = ""


class ASRRequest(BaseModel):
    scene_id: str
    audioBase64: str = Field(..., min_length=1)
    mimeType: str = "audio/webm"


class ASRResponse(BaseModel):
    provider: str
    text: str = ""
    degraded: bool = False
    fallback: str = "browser"
    error: str = ""
