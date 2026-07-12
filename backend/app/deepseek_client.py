from .llm import DeepSeekProvider


def call_deepseek(messages: list[dict], timeout: int = 10) -> str | None:
    result = DeepSeekProvider().chat(messages, timeout=timeout)
    return result.content if result.ok else None
