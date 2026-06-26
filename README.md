# 냉채 (Naengchae)

냉장고에 있는 재료와 조리 환경(전자레인지만 / 가스레인지 1구 / 풀옵션)을 입력하면, RAG 기반
에이전트가 실제로 만들 수 있는 레시피 3개를 추천해주는 개인 사이드 프로젝트입니다.

## 이 프로젝트의 차별점

부트캠프 Langchain 실습(팀 단위 과제)에서 멈추지 않고, **MLOps/LLMOps 파이프라인을 직접
구축하고 인프라와 연동해, 모바일 앱 + 백엔드 + 배포까지 끝까지 이어지는 실제 동작하는
애플리케이션으로 완성하는 것**이 목표입니다. 에이전트 하나를 잘 만드는 것보다, 평가 →
관찰성(observability) → 신뢰성 → 배포로 이어지는 운영 파이프라인 전체를 갖추는 쪽에
집중합니다.

그리고 그 과정에서 만난 문제들(환경 충돌, 검증 로직 버그, git 히스토리 충돌 등)을 어떻게
진단했고 어떤 전략으로 풀어갔는지를 [`docs/ENGINEERING_LOG.md`](docs/ENGINEERING_LOG.md)에
상세히 기록해두었습니다 — 이 프로젝트에서는 결과물만큼 그 과정의 의사결정도 중요한
산출물입니다.

## 구조

```
naengchae-langchain/naengchae_chain/   # LangGraph RAG 에이전트 (핵심)
  ├─ models.py        # UserProfile / FridgeIngredient / Recipe / RecipeRecommendation (Pydantic)
  ├─ prompts.py        # 단순 체인용 + RAG/피드백 포함 에이전트용 프롬프트
  ├─ chain.py           # 단순 prompt | llm.with_structured_output 체인
  ├─ graph.py           # retrieve → generate → validate → retry(최대 2회) LangGraph
  └─ knowledge_base.py  # FAISS 기반 조리 지식 코퍼스
naengchae-langchain/eval/              # 평가 하니스 (Phase 1) + retrieval 평가 (Phase 3)
naengchae-langchain/observability/      # 관찰성 문서 + 샘플 로그 (Phase 2)
web/                                    # FastAPI 데모 (Upstage solar-pro3 연동)
src/                                    # Expo/React Native 모바일 앱 (온보딩 완성, 메인 탭은 placeholder)
```

## 핵심 아이디어: 검증·재시도 루프

`graph.py`의 LangGraph는 LLM이 생성한 레시피를 결정론적 규칙으로 다시 검증합니다.

1. **retrieve**: 보유 재료 + 조리환경 + 음식취향으로 FAISS에서 관련 조리 지식 검색
2. **generate**: 검색된 컨텍스트 + (있다면) 이전 시도의 실패 피드백을 프롬프트에 넣어 구조화된
   레시피 3개 생성
3. **validate**: 아래 3가지를 코드로 직접 검증
   - 조리환경에서 쓸 수 없는 조리법(예: 전자레인지 환경에서 오븐/팬 요리)을 추천했는가
   - `usedIngredients`에 적힌 재료가 실제 보유 재료 목록에 있는가
   - 유통기한이 임박한 재료를 실제로 활용했는가
4. 검증 실패 시 실패 사유를 피드백으로 넘겨 최대 2회까지 재생성

## Phase 1: 평가(Evaluation) 파이프라인 — LLMOps의 첫 단계 (2026-06)

LLMOps 파이프라인의 첫 조각으로, 합성 테스트케이스 24건으로 에이전트의 통과율을 측정하고
실패를 분석해 실제로 개선했다는 것을 수치로 보였습니다. 자세한 방법론과 발견한 버그/수정 내역은
[`naengchae-langchain/eval/README.md`](naengchae-langchain/eval/README.md)에,
이 과정에서의 의사결정과 문제 해결 전략은 [`docs/ENGINEERING_LOG.md`](docs/ENGINEERING_LOG.md)에
정리했습니다.

| 지표 | 베이스라인 | 2회 개선 후 |
|---|---|---|
| 최종 통과율 | 70.8% | **91.7%** |
| 1차 통과율(재시도 없이) | 54.2% | **70.8%** |
| 평균 재시도 횟수 | 1.08 | **0.5** |

가장 영향이 컸던 발견: 검증 로직이 전자레인지 환경에서 "찜" 조리법을 금지하고 있었는데, 정작
RAG 지식베이스는 전자레인지에 계란찜·단호박찜이 적합하다고 명시하고 있어 둘이 서로 모순됐던
버그를 찾아 수정.

## Phase 2: Observability — 구조화 로깅 + 토큰/비용 추적 (2026-06)

retrieve/generate/validate 각 단계와 요청 전체를 `trace_id`로 묶어 JSON Lines로 기록하고,
LLM 호출마다 실제 토큰 사용량과 비용(Upstage 공식 가격 기준)을 계산합니다. 자세한 이벤트
스키마와 샘플 로그는 [`naengchae-langchain/observability/README.md`](naengchae-langchain/observability/README.md)에 있습니다.

| 항목 (평가셋 24건 1회 실행 기준) | 값 |
|---|---|
| 총 LLM 호출(재시도 포함) | 37회 |
| 총 토큰 | 76,400 |
| 총 추정 비용 | $0.0134 |

Phase 1의 재시도율 개선이 통과율뿐 아니라 비용에도 직접 영향을 준다는 것을 수치로 확인했습니다
(평균 재시도 0.62회가 LLM 호출 수를 24회→37회로 54% 늘림).

## Phase 3: RAG 코퍼스 확장 + Retrieval 품질 평가 (2026-06)

지식 코퍼스를 17~18개 → 94개 문서로 확장하고(`eval/cases.json`에 실제 등장하는 재료 31종 전수
커버), retrieval 품질을 "랭킹이 정확한가"와 "코퍼스에 정보가 애초에 있는가"로 나눠 측정했습니다.
자세한 방법론·한계·k값 결정 이유는
[`naengchae-langchain/eval/RETRIEVAL_EVAL.md`](naengchae-langchain/eval/RETRIEVAL_EVAL.md)에
있습니다.

| 지표 (질의 38건 기준) | k=4 (현재 운영값) | k=8 |
|---|---|---|
| hit_rate | 1.0 | 1.0 |
| recall | 0.900 | 0.951 |
| MRR | 0.95 | 0.95 |

k=8이 recall을 5.1%p 올리지만 컨텍스트(=비용)가 최대 2배 늘어나는 비용 대비 이득이 작아 k=4를
유지했습니다. 코퍼스 확장 자체는 질의 38건 중 최소 10건(보수적 추정)을 구버전에서 전혀 답할 수
없던 주제에서 새로 답할 수 있게 만들었습니다.

**부수 효과:** 코퍼스를 확장한 뒤 Phase 1의 24개 에이전트 평가셋을 다시 돌려보니 최종 통과율이
91.7%→**95.8%**로 올랐습니다(회귀 없음을 확인하려고 돌린 것인데 오히려 개선됨). 조리환경×취향
조합 문서(combo-*)가 그동안 반복적으로 실패하던 "전자레인지+고단백" 케이스를 직접 해결했습니다.

## Phase 4-1: 백엔드 영속화 + 웹으로 먼저 검증 (2026-06, 진행 중)

모바일 화면(`FridgeScreen`/`RecipeScreen`)을 만들기 전에, 같은 API로 동작할 백엔드 영속화를
먼저 만들고 **웹 데모로 먼저 검증**했습니다 — 모바일(Expo) 쪽 반복 주기가 느려서, API 계약과
화면 흐름은 브라우저에서 먼저 확정하는 게 더 빠르다고 판단했습니다.

- `naengchae_chain/db.py`: SQLite + SQLModel로 냉장고 재료·사용자 프로필 영속화 (단일 사용자
  가정 — 인증이 아직 없어 사용자 구분 자체가 별도 범위의 작업이라고 판단해 지금 단계에서는
  넣지 않기로 함)
- `/fridge`(GET/POST/DELETE), `/profile`(GET/POST) API 추가
- `/recommend`를 `{today}`만 받도록 변경 — 프로필·재료는 이제 DB에서 읽음(기존 클라이언트와
  호환되지 않는 변경이지만, 영향 범위를 확인해 Phase 1~3 평가 하니스는 이 API를 거치지 않아
  무관함을 확인)
- `web/static/index.html`을 메모리 상태 대신 위 API로 동작하도록 교체 — 새로고침해도 재료/
  프로필이 남는지 Python `urllib`로 전체 흐름(저장→추가→조회→추천→삭제→404)을 직접 호출해
  검증
- 자세한 결정 이유(왜 웹 먼저, 왜 단일 사용자, 왜 SQLModel, 왜 API 계약을 바꿨는지)는
  `docs/ENGINEERING_LOG.md`에 기록

다음 작업: 같은 API를 모바일 `FridgeScreen.js`/`RecipeScreen.js`에 연동(포팅), 이후
`ReportScreen`(재료 활용률 등)은 추천 히스토리 기록이 더 필요해 별도로 다룹니다.

## 실행 방법

### 평가 하니스
```bash
cd naengchae-langchain
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "UPSTAGE_API_KEY=..." > .env
python3 eval/run_eval.py
```

### 웹 데모
```bash
cd web
pip install -r ../naengchae-langchain/requirements.txt fastapi uvicorn
uvicorn main:app --reload
```

### 모바일 앱
```bash
npm install
npx expo start
```

## 로드맵 (MLOps/LLMOps 파이프라인 → 실제 애플리케이션)

1. ✅ 평가(Evaluation) 파이프라인 — 합성 테스트케이스로 통과율 측정 및 개선
2. ✅ Observability — retrieve/generate/validate 구조화 로깅, 토큰/비용/지연시간 트래킹
3. ✅ RAG 코퍼스 확장 + retrieval 품질 평가
4. 🟡 백엔드 영속화(DB) + 모바일 화면 실제 구현·연동 — 백엔드+웹 검증 완료, 모바일 포팅 진행 중
5. ⬜ 신뢰성 강화 — 단위 테스트, LLM 실패 폴백, 캐싱
6. ⬜ 배포 + 데모 자료

각 단계에서 만난 문제와 해결 전략은 [`docs/ENGINEERING_LOG.md`](docs/ENGINEERING_LOG.md)에 계속
누적해서 기록합니다.
