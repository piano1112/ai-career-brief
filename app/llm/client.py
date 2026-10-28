"""모든 Claude API 호출의 단일 진입점 (SPEC 2: 비용 추적과 모델 교체를 한 곳에서).

- 모델명은 CLAUDE_MODEL 환경변수로 받는다 (하드코딩 금지).
- 거절(refusal) 대비: 서버 측 fallback을 기본으로 켠다. 안전 분류기가 요청을 거절하면
  Anthropic이 권장하는 다른 모델로 서버가 자동 재시도한다 (decisions 012).
- 스트리밍: 글자 조각(TextDelta)을 바로 넘기고, 끝나면 완성된 메시지(Final)를 넘긴다.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache

import anthropic

from app.config import get_settings
from app.llm.usage import record_usage

FALLBACK_BETA = "server-side-fallback-2026-07-01"


class LlmNotConfiguredError(RuntimeError):
    pass


@dataclass
class TextDelta:
    text: str


@dataclass
class Final:
    message: object  # anthropic BetaMessage: .content, .stop_reason, .model, .usage


@lru_cache
def _client() -> anthropic.Anthropic:
    settings = get_settings()
    if not settings.anthropic_api_key or not settings.claude_model:
        raise LlmNotConfiguredError("ANTHROPIC_API_KEY와 CLAUDE_MODEL을 .env에 설정하세요.")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def stream_message(
    *, purpose: str, system: str, messages: list[dict], tools: list[dict]
) -> Iterator[TextDelta | Final]:
    """Claude에 요청 1번. purpose는 llm_usage에 남길 용도 이름 (예: "chat")."""
    settings = get_settings()
    with _client().beta.messages.stream(
        model=settings.claude_model,
        max_tokens=settings.claude_max_tokens,
        system=system,
        messages=messages,
        tools=tools,
        output_config={"effort": settings.claude_effort},
        # 대화 기록이 append-only라서 앞부분이 매번 같다 → 자동 캐시로 입력 비용 절감
        cache_control={"type": "ephemeral"},
        betas=[FALLBACK_BETA],
        fallbacks="default",
    ) as stream:
        for event in stream:
            if event.type == "text":
                yield TextDelta(event.text)
        message = stream.get_final_message()

    # fallback이 일어나면 message.model이 실제로 답한 모델이다.
    record_usage(purpose, message.model, message.usage)
    yield Final(message)
