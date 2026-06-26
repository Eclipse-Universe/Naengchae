# invoke_with_retry()에 대한 단위 테스트입니다. 실제 LLM을 호출하지 않고, 일부러
# 실패하는 가짜 함수로 "몇 번 재시도하는지" / "결국 실패하면 어떤 예외로 감싸는지"를
# 검증합니다. 재시도 사이 대기시간(exponential backoff)이 있어서 너무 많은 재시도를
# 요구하는 테스트는 느려질 수 있으므로, LLM_CALL_MAX_ATTEMPTS(3번) 이내로만 검증합니다.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from naengchae_chain.errors import LLMUnavailableError
from naengchae_chain.graph import invoke_with_retry


def test_succeeds_on_first_try_without_retrying():
    calls = []

    def fn():
        calls.append(1)
        return "ok"

    assert invoke_with_retry(fn) == "ok"
    assert len(calls) == 1


def test_succeeds_after_transient_failures():
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 2:
            raise ConnectionError("일시적인 네트워크 오류")
        return "recovered"

    assert invoke_with_retry(flaky) == "recovered"
    assert len(calls) == 2


def test_raises_llm_unavailable_error_after_exhausting_retries():
    calls = []

    def always_fails():
        calls.append(1)
        raise TimeoutError("계속 타임아웃")

    with pytest.raises(LLMUnavailableError):
        invoke_with_retry(always_fails)

    # LLM_CALL_MAX_ATTEMPTS(3)번까지만 시도하고 멈춰야 한다.
    assert len(calls) == 3


def test_passes_through_args_and_kwargs():
    def fn(a, b, c=None):
        return (a, b, c)

    assert invoke_with_retry(fn, 1, 2, c=3) == (1, 2, 3)
