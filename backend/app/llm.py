from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from .logging_config import log_error, log_event


@dataclass
class LLMResult:
    content: str | None
    provider: str
    ok: bool
    degraded: bool = False
    error: str = ""
    duration_ms: int = 0
    attempts: int = 1


class LLMProvider(Protocol):
    name: str

    def chat(self, messages: list[dict[str, str]], timeout: int = 10, max_tokens: int = 0) -> LLMResult:
        ...


class DeepSeekProvider:
    name = "deepseek"

    def __init__(self) -> None:
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat/completions")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    def chat(self, messages: list[dict[str, str]], timeout: int = 10, max_tokens: int = 0) -> LLMResult:
        started = time.perf_counter()
        if not self.api_key:
            return LLMResult(None, self.name, False, True, "missing_api_key")
        if quota_is_low(self.name):
            return LLMResult(None, self.name, False, True, "quota_low")
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": max_tokens if max_tokens > 0 else 1200,
        }
        request = urllib.request.Request(
            self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        max_attempts = max(1, int(os.getenv("LLM_RETRY_ATTEMPTS", "2")))
        last_error = "unknown"
        for attempt in range(1, max_attempts + 1):
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    data = json.loads(response.read().decode("utf-8"))
                duration_ms = int((time.perf_counter() - started) * 1000)
                return LLMResult(data["choices"][0]["message"]["content"], self.name, True, duration_ms=duration_ms, attempts=attempt)
            except urllib.error.HTTPError as exc:
                duration_ms = int((time.perf_counter() - started) * 1000)
                last_error = classify_http_error(exc.code)
                retryable = exc.code in {429, 500, 502, 503, 504}
                if not retryable or attempt == max_attempts:
                    return LLMResult(None, self.name, False, retryable, last_error, duration_ms, attempts=attempt)
                time.sleep(0.25 * attempt)
            except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError, TimeoutError) as exc:
                duration_ms = int((time.perf_counter() - started) * 1000)
                last_error = exc.__class__.__name__
                if attempt == max_attempts:
                    return LLMResult(None, self.name, False, True, last_error, duration_ms, attempts=attempt)
                time.sleep(0.25 * attempt)
        duration_ms = int((time.perf_counter() - started) * 1000)
        return LLMResult(None, self.name, False, True, last_error, duration_ms, attempts=max_attempts)


class PlaceholderProvider:
    def __init__(self, name: str, key_env: str) -> None:
        self.name = name
        self.key_env = key_env

    def chat(self, messages: list[dict[str, str]], timeout: int = 10, max_tokens: int = 0) -> LLMResult:
        if not os.getenv(self.key_env):
            return LLMResult(None, self.name, False, True, "missing_api_key")
        return LLMResult(None, self.name, False, True, "provider_not_implemented")


def configured_providers() -> list[LLMProvider]:
    order = os.getenv("LLM_PROVIDER_ORDER", "deepseek,qwen,wenxin")
    providers: dict[str, LLMProvider] = {
        "deepseek": DeepSeekProvider(),
        "qwen": PlaceholderProvider("qwen", "QWEN_API_KEY"),
        "wenxin": PlaceholderProvider("wenxin", "WENXIN_API_KEY"),
    }
    return [providers[name] for name in (item.strip() for item in order.split(",")) if name in providers]


def chat_with_failover(messages: list[dict[str, str]], timeout: int = 10, max_tokens: int = 0) -> LLMResult:
    last_result = LLMResult(None, "fallback", False, True, "no_provider")
    for provider in configured_providers():
        result = provider.chat(messages, timeout=timeout, max_tokens=max_tokens)
        if result.ok and result.content:
            log_event("llm_success", provider=result.provider, duration_ms=result.duration_ms, attempts=result.attempts)
            return result
        last_result = result
        log_error("llm_failed", provider=result.provider, error=result.error, duration_ms=result.duration_ms, attempts=result.attempts)
    return last_result


def classify_http_error(status_code: int) -> str:
    if status_code == 401:
        return "auth_failed"
    if status_code == 403:
        return "permission_denied"
    if status_code == 429:
        return "rate_limited_or_quota_exceeded"
    if status_code >= 500:
        return "provider_unavailable"
    return f"http_{status_code}"


def quota_is_low(provider: str) -> bool:
    remaining = os.getenv(f"{provider.upper()}_QUOTA_REMAINING")
    threshold = int(os.getenv("LLM_QUOTA_WARN_THRESHOLD", "0"))
    if remaining is None or threshold <= 0:
        return False
    try:
        return int(remaining) <= threshold
    except ValueError:
        return False


def model_status() -> list[dict[str, str | bool | int]]:
    statuses = []
    for provider in configured_providers():
        name = provider.name
        remaining = os.getenv(f"{name.upper()}_QUOTA_REMAINING", "")
        configured = bool(getattr(provider, "api_key", None)) if isinstance(provider, DeepSeekProvider) else bool(os.getenv(getattr(provider, "key_env", "")))
        statuses.append(
            {
                "provider": name,
                "configured": configured,
                "quotaRemaining": remaining,
                "quotaLow": quota_is_low(name),
            }
        )
    return statuses
