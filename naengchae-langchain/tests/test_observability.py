# observability.py의 토큰/비용 계산 함수에 대한 단위 테스트입니다.
# 이 숫자들이 Phase 2 브리핑("24건 -> $0.0134")의 근거이기 때문에, 계산식이
# 조용히 깨지면 그 숫자 전체가 틀려집니다 - 가격표가 바뀔 일은 있어도 계산식 자체는
# 고정해둘 가치가 있습니다.

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from naengchae_chain.observability import estimate_cost_usd, extract_usage, summarize_usage


def test_estimate_cost_usd_known_model():
    # solar-pro3: input $0.15/1M, cached input $0.015/1M, output $0.6/1M
    cost = estimate_cost_usd("solar-pro3", input_tokens=1000, output_tokens=500, cached_tokens=0)
    expected = (1000 * 0.15 + 500 * 0.60) / 1_000_000
    assert cost == round(expected, 8)


def test_estimate_cost_usd_with_cached_tokens():
    cost = estimate_cost_usd("solar-pro3", input_tokens=1000, output_tokens=0, cached_tokens=800)
    # 800개는 캐시 단가, 나머지 200개는 일반 입력 단가
    expected = (200 * 0.15 + 800 * 0.015) / 1_000_000
    assert cost == round(expected, 8)


def test_estimate_cost_usd_unknown_model_returns_none():
    assert estimate_cost_usd("gpt-unknown-model", 100, 100) is None


def test_extract_usage_reads_usage_metadata():
    ai_message = SimpleNamespace(
        usage_metadata={
            "input_tokens": 1000,
            "output_tokens": 200,
            "total_tokens": 1200,
            "input_token_details": {"cache_read": 300},
        }
    )
    usage = extract_usage(ai_message, "solar-pro3")
    assert usage["input_tokens"] == 1000
    assert usage["output_tokens"] == 200
    assert usage["total_tokens"] == 1200
    assert usage["cached_tokens"] == 300
    assert usage["cost_usd"] is not None


def test_extract_usage_missing_usage_metadata_defaults_to_zero():
    # provider가 usage_metadata를 안 채워주는 경우에도 죽지 않아야 한다.
    ai_message = SimpleNamespace(usage_metadata=None)
    usage = extract_usage(ai_message, "solar-pro3")
    assert usage["input_tokens"] == 0
    assert usage["output_tokens"] == 0
    assert usage["cached_tokens"] == 0


def test_summarize_usage_sums_across_retries():
    usage_list = [
        {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150, "cost_usd": 0.001},
        {"input_tokens": 110, "output_tokens": 40, "total_tokens": 150, "cost_usd": 0.0009},
    ]
    summary = summarize_usage(usage_list)
    assert summary["llm_calls"] == 2
    assert summary["total_input_tokens"] == 210
    assert summary["total_output_tokens"] == 90
    assert summary["total_tokens"] == 300
    assert summary["total_cost_usd"] == round(0.001 + 0.0009, 8)


def test_summarize_usage_empty_list():
    summary = summarize_usage([])
    assert summary["llm_calls"] == 0
    assert summary["total_cost_usd"] is None
