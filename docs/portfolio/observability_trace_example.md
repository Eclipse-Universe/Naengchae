# 포트폴리오용 캡처: 구조화 로그(observability) 한 트레이스

출처: `naengchae-langchain/observability/sample_log.jsonl` (실제 실행 결과, 가공 없음)

이 트레이스 하나가 이 프로젝트의 핵심 루프(검증 실패 → 재시도 → 통과)와
관찰성(토큰/비용/지연시간 추적)을 동시에 보여줍니다. 코드 에디터나 터미널에서
아래 JSON을 pretty-print해서 캡처하면 좋습니다.

```json
{"ts": "2026-06-25T17:05:06.310+00:00", "event": "request_start", "trace_id": "2114e578-...", "household_type": "family", "member_count": 3, "cooking_env": "oneburner", "food_preference": ["korean"], "num_ingredients": 4, "num_expiring": 3}
{"ts": "2026-06-25T17:05:06.424+00:00", "event": "retrieve", "trace_id": "2114e578-...", "duration_ms": 112.4, "query_chars": 162, "num_docs": 4}
{"ts": "2026-06-25T17:05:14.420+00:00", "event": "generate", "trace_id": "2114e578-...", "attempt": 1, "duration_ms": 7994.7, "model": "solar-pro3", "input_tokens": 1605, "output_tokens": 487, "total_tokens": 2092, "cached_tokens": 1280, "cost_usd": 0.00036015}
{"ts": "2026-06-25T17:05:14.421+00:00", "event": "validate", "trace_id": "2114e578-...", "duration_ms": 0.0, "valid": false, "retry_count": 1, "num_issues": 1}
{"ts": "2026-06-25T17:05:21.956+00:00", "event": "generate", "trace_id": "2114e578-...", "attempt": 2, "duration_ms": 7535.1, "model": "solar-pro3", "input_tokens": 1634, "output_tokens": 454, "total_tokens": 2088, "cached_tokens": 1280, "cost_usd": 0.0003447}
{"ts": "2026-06-25T17:05:21.957+00:00", "event": "validate", "trace_id": "2114e578-...", "duration_ms": 0.0, "valid": true, "retry_count": 1, "num_issues": 0}
{"ts": "2026-06-25T17:05:21.957+00:00", "event": "request_end", "trace_id": "2114e578-...", "duration_ms": 15647.2, "valid": true, "retry_count": 1, "llm_calls": 2, "total_input_tokens": 3239, "total_output_tokens": 941, "total_tokens": 4180, "total_cost_usd": 0.00070485}
```

## 캡션으로 쓸 수 있는 한 줄 설명

> 1차 생성(attempt 1)이 검증을 통과 못 하자(valid: false) 실패 이유를 피드백으로 받아
> 2차 생성(attempt 2)에서 통과했고, 이 요청 전체의 비용은 $0.0007, 지연시간은 15.6초였다 —
> `trace_id`로 5개 이벤트를 추적해 "왜 느렸는지/왜 비쌌는지/왜 재시도했는지"를 사후에
> 그대로 재구성할 수 있다.

## 캡처 방법 제안
- VS Code나 터미널에서 `cat naengchae-langchain/observability/sample_log.jsonl | python3 -m json.tool` 같은 식으로 한 줄씩 pretty-print해서 캡처
- 또는 `jq` 설치돼 있으면 `cat sample_log.jsonl | jq .`로 색깔까지 입혀서 캡처하면 더 보기 좋음
