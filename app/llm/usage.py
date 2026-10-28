"""LLM 호출 1번마다 토큰 수와 추정 비용을 llm_usage 테이블에 남긴다 (SPEC 2 코드 원칙)."""

import logging

from app.db.models import LlmUsage
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

# 100만 토큰당 USD: (입력, 출력). 2026-10 확인 (docs/costs.md).
# 캐시 쓰기 = 입력의 1.25배, 캐시 읽기 = 아래 CACHE_READ 값 (없으면 입력의 0.1배).
PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),  # 거절 시 fallback 대상이 될 수 있는 모델
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}
CACHE_READ: dict[str, float] = {"claude-opus-5-5": 0.20, "claude-sonnet-5-5": 0.20}


def estimate_cost(
    model: str, input_tokens: int, output_tokens: int, cache_write: int, cache_read: int
) -> float:
    if model not in PRICES:
        logger.warning("가격표에 없는 모델 %s → 비용 0으로 기록 (PRICES에 추가 필요)", model)
        return 0.0
    price_in, price_out = PRICES[model]
    price_cache_read = CACHE_READ.get(model, price_in * 0.1)
    cost = (
        input_tokens * price_in
        + cache_write * price_in * 1.25
        + cache_read * price_cache_read
        + output_tokens * price_out
    )
    return cost / 1_000_000


def record_usage(purpose: str, model: str, usage) -> None:  # usage: SDK의 Usage 객체
    """input_tokens 컬럼에는 캐시 읽기·쓰기를 포함한 전체 입력 토큰을 저장한다."""
    cache_write = usage.cache_creation_input_tokens or 0
    cache_read = usage.cache_read_input_tokens or 0
    row = LlmUsage(
        purpose=purpose,
        model=model,
        input_tokens=usage.input_tokens + cache_write + cache_read,
        output_tokens=usage.output_tokens,
        est_cost_usd=estimate_cost(
            model, usage.input_tokens, usage.output_tokens, cache_write, cache_read
        ),
    )
    # 호출한 쪽의 DB 세션과 분리: 대화 처리가 롤백돼도 비용 기록은 남아야 한다.
    with SessionLocal() as session:
        session.add(row)
        session.commit()
