# 관찰성 (Observability) — Phase 2

`naengchae_chain.observability` 모듈이 `graph.py`의 retrieve/generate/validate 각 단계와
요청 전체(request_start/request_end)를 JSON Lines로 기록한다. 같은 요청에 속한 이벤트는
모두 같은 `trace_id`를 갖는다.

## 왜 필요한가

Phase 1(평가 하니스)은 "통과했는지"만 알려준다. 실제로 운영하려면 "**얼마나 걸렸는지**,
**얼마짜리인지**, **재시도가 비용/지연에 얼마나 영향을 주는지**"를 알아야 한다. 이 셋을
모르면 프롬프트를 한 줄 고칠 때마다 비용이 어떻게 바뀌는지, 재시도 루프가 실제로 얼마나
비싼지 전혀 알 수 없다.

## 이벤트 스키마

| event | 의미 | 주요 필드 |
|---|---|---|
| `request_start` | 요청 시작 | `household_type`, `cooking_env`, `food_preference`, `num_ingredients`, `num_expiring` |
| `retrieve` | RAG 검색 1회 | `duration_ms`, `query_chars`, `num_docs` |
| `generate` | LLM 생성 1회 (재시도마다 별도 기록) | `attempt`, `duration_ms`, `model`, `input_tokens`, `output_tokens`, `cached_tokens`, `cost_usd` |
| `validate` | 결정론적 검증 1회 | `duration_ms`, `valid`, `retry_count`, `num_issues` |
| `request_end` | 요청 종료 (재시도 전부 끝난 뒤) | `duration_ms`(전체), `valid`, `retry_count`, `llm_calls`, `total_tokens`, `total_cost_usd` |

샘플 트레이스(재시도 1회 포함, 실제 평가 실행에서 추출): [`sample_log.jsonl`](sample_log.jsonl)

## 토큰/비용 추적 방법

`generate_node`에서 `llm.with_structured_output(RecipeRecommendation, include_raw=True)`를
사용한다. `include_raw=True`를 켜면 파싱된 결과(`parsed`)뿐 아니라 원본 `AIMessage`(`raw`)도
함께 받을 수 있고, `raw.usage_metadata`에 실제 input/output 토큰 수가 들어있다. 이걸 끄면
구조화된 Pydantic 객체만 받고 토큰 정보는 버려진다.

가격표(`observability.py`의 `PRICING_PER_MILLION_TOKENS`)는
[Upstage 공식 가격 페이지](https://www.upstage.ai/pricing/api)를 2026-06-25에 확인해 반영했다
(`solar-pro3`: input $0.15/1M, 캐시 input $0.015/1M, output $0.6/1M tokens). 가격은 바뀔 수
있으므로 실제 청구서와 차이가 나면 이 표를 갱신해야 한다.

**범위에서 제외한 것:** RAG 검색(retrieve) 단계에서도 쿼리 텍스트를 임베딩하느라 Upstage
Embeddings API를 호출하지만, LangChain의 `Embeddings.embed_query()` 인터페이스는 토큰
사용량을 반환하지 않는다(채팅 모델의 `usage_metadata`와 달리 표준화돼 있지 않음). 정확히
추적하려면 LangChain 래퍼를 거치지 않고 Upstage 클라이언트를 직접 호출해야 하는데, 임베딩
비용 자체가 토큰당 단가($0.10/1M)도 낮고 비중도 작아 이번 단계에서는 `retrieve`의 지연시간만
추적하고 토큰/비용 추적은 `generate`(실제 비용이 발생하는 LLM 호출) 단계에만 정확히
구현했다.

## 실제 측정값 (24개 평가 케이스 1회 실행)

| 항목 | 값 |
|---|---|
| 총 요청 | 24건 |
| 총 LLM 호출(재시도 포함) | 37회 |
| 총 토큰 | 76,400 |
| 총 추정 비용 | $0.0134 |

평균 재시도 0.62회(이 실행 기준)가 LLM 호출 수를 24회에서 37회로 54% 늘렸다 — Phase 1에서
재시도율을 낮추는 프롬프트 개선이 통과율뿐 아니라 **비용에도 직접 영향**을 준다는 것을
수치로 보여준다.

## 로그 위치

- stdout: 컨테이너/배포 환경에서 표준 로그 수집기가 그대로 가져갈 수 있도록.
- `naengchae-langchain/logs/naengchae.jsonl`: 로컬 개발 시 누적 파일 (gitignore 처리,
  런타임 산출물이라 커밋하지 않음).
