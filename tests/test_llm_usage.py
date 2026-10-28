import pytest

from app.llm.usage import estimate_cost


def test_estimate_cost_opus() -> None:
    # 입력 1M $4 + 캐시 쓰기 1M $5 + 캐시 읽기 1M $0.20 + 출력 1M $20
    cost = estimate_cost("claude-opus-5-5", 1_000_000, 1_000_000, 1_000_000, 1_000_000)
    assert cost == pytest.approx(29.2)


def test_unknown_model_costs_zero() -> None:
    assert estimate_cost("unknown-model", 100, 100, 0, 0) == 0.0
