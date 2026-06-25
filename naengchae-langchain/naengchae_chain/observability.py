"""구조화 로깅 + LLM 토큰/비용 추적.

retrieve/generate/validate 각 단계와 요청 전체를 JSON Lines 형식으로 기록한다.
컨테이너 환경에서는 stdout만 보는 경우가 많아 stdout에도 같은 내용을 출력하고,
로컬 개발/데모용으로 파일에도 누적 저장한다.

가격표 출처: https://www.upstage.ai/pricing/api (확인일: 2026-06-25, VAT 별도).
가격은 언제든 바뀔 수 있으므로, 실제 청구 금액과 차이가 나면 이 표를 갱신할 것.
"""

import json
import logging
import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = Path(os.environ.get("NAENGCHAE_LOG_DIR", PACKAGE_ROOT / "logs"))

# $ / 1M tokens. (model, 종류) -> 단가
PRICING_PER_MILLION_TOKENS: dict[str, dict[str, float]] = {
    "solar-pro3": {"input": 0.15, "input_cached": 0.015, "output": 0.60},
    "solar-embedding-1-large": {"input": 0.10, "input_cached": 0.10, "output": 0.0},
}


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("naengchae")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(stream_handler)

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(LOG_DIR / "naengchae.jsonl", encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(file_handler)
    except OSError:
        # 로그 디렉터리를 만들 수 없는 환경(예: 읽기 전용 파일시스템)이면 stdout만 사용.
        pass

    return logger


_logger = _build_logger()


def log_event(event: str, trace_id: str, **fields: Any) -> dict:
    """이벤트 1건을 JSON Lines로 stdout + 로그 파일에 기록하고, 기록한 dict를 반환한다."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "event": event,
        "trace_id": trace_id,
        **fields,
    }
    _logger.info(json.dumps(record, ensure_ascii=False))
    return record


@contextmanager
def timed() -> Iterator[dict]:
    """with timed() as t: ... 끝나면 t['duration_ms']에 경과 시간이 채워진다."""
    result: dict = {}
    start = time.perf_counter()
    try:
        yield result
    finally:
        result["duration_ms"] = round((time.perf_counter() - start) * 1000, 1)


def estimate_cost_usd(
    model: str, input_tokens: int, output_tokens: int, cached_tokens: int = 0
) -> Optional[float]:
    """모델별 단가로 USD 비용을 추정한다. 가격표에 없는 모델이면 None."""
    pricing = PRICING_PER_MILLION_TOKENS.get(model)
    if pricing is None:
        return None

    uncached_input = max(input_tokens - cached_tokens, 0)
    cost = (
        uncached_input * pricing["input"]
        + cached_tokens * pricing["input_cached"]
        + output_tokens * pricing["output"]
    ) / 1_000_000
    return round(cost, 8)


def extract_usage(ai_message: Any, model: str) -> dict:
    """AIMessage.usage_metadata에서 토큰 수를 뽑아 비용까지 계산한 dict로 반환한다.

    usage_metadata가 없는 경우(provider가 안 채워주는 경우)에도 죽지 않고 0으로 채운다.
    """
    usage = getattr(ai_message, "usage_metadata", None) or {}
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    cached_tokens = (usage.get("input_token_details") or {}).get("cache_read", 0)

    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": usage.get("total_tokens", input_tokens + output_tokens),
        "cached_tokens": cached_tokens,
        "cost_usd": estimate_cost_usd(model, input_tokens, output_tokens, cached_tokens),
    }


def summarize_usage(usage_list: list[dict]) -> dict:
    """generate 단계에서 재시도마다 쌓인 usage dict 리스트를 합산한다."""
    total_input = sum(u["input_tokens"] for u in usage_list)
    total_output = sum(u["output_tokens"] for u in usage_list)
    total_tokens = sum(u["total_tokens"] for u in usage_list)
    costs = [u["cost_usd"] for u in usage_list if u["cost_usd"] is not None]
    return {
        "llm_calls": len(usage_list),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_tokens": total_tokens,
        "total_cost_usd": round(sum(costs), 8) if costs else None,
    }
