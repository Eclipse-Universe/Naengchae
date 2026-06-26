# 냉채(Naengchae) — 포트폴리오 요약

이 문서 하나로 프로젝트 전체를 훑고 포트폴리오/이력서에 옮길 내용을 바로 뽑을 수 있게
정리했습니다. 더 깊은 내용은 각 링크를 따라가세요.

- **저장소**: https://github.com/Eclipse-Universe/Naengchae
- **라이브 데모**: https://naengchae-web.onrender.com/
  ⚠️ 무료 PostgreSQL이 생성 후 30일+14일 유예 후 만료되니, 포트폴리오 공개 시점에 데모가
  살아있는지 먼저 확인하세요(생성일 기준 약 44일 — 정확한 만료일은 Render 대시보드에서
  확인 가능).
- **전체 진행 기록**: [`README.md`](README.md), [`docs/ENGINEERING_LOG.md`](docs/ENGINEERING_LOG.md)

## 한 줄 소개

냉장고 보유 재료 + 조리 환경을 입력하면 LangGraph 기반 RAG 에이전트가 실제로 만들 수 있는
레시피를 추천하는 앱. **에이전트를 잘 만드는 것보다, 평가→관찰성→신뢰성→배포로 이어지는
LLMOps 파이프라인 전체를 갖추고 모바일+백엔드+배포까지 끝까지 연결된 실제 동작하는
애플리케이션으로 완성하는 것**에 집중한 개인 사이드 프로젝트.

## 기술 스택

| 영역 | 사용 기술 |
|---|---|
| LLM/Agent | LangGraph, LangChain, Upstage `solar-pro3`/`solar-embedding-1-large` |
| 검색(RAG) | FAISS, 자체 작성 조리 지식 코퍼스 94개 문서 |
| 백엔드 | FastAPI, SQLModel(SQLite/PostgreSQL 겸용), Pydantic |
| 모바일 | Expo(React Native), React Navigation |
| 신뢰성 | pytest(39개 단위 테스트), tenacity(재시도) |
| 배포 | Render(Blueprint, 무료 웹서비스+PostgreSQL) |
| 관찰성 | 자체 JSON Lines 구조화 로깅 + 토큰/비용 추적 |

## 핵심 수치 (전부 실측, 가공 없음)

| Phase | 측정 | 베이스라인 | 결과 |
|---|---|---|---|
| 1. 평가 | 24개 합성 케이스 최종 통과율 | 70.8% | **95.8%**(Phase 3 코퍼스 확장 후 재측정) |
| 1. 평가 | 1차 통과율(재시도 없이) | 54.2% | 70.8% |
| 2. Observability | 24건 실행 시 LLM 호출/토큰/비용 | — | 37회 호출, 76,400 토큰, $0.0134 |
| 3. Retrieval | 38개 질의 기준 hit_rate/recall/MRR (k=4) | — | 1.0 / 0.900 / 0.95 |
| 3. 코퍼스 | 지식베이스 문서 수 | 17~18개 | 94개 |
| 5. 캐싱 | 동일 요청 재호출 시간 | 6.04초(LLM 3회 재시도) | 0.00초(캐시 히트, 비용 $0) |
| 5. 테스트 | 단위 테스트 수 / 실행 시간 | 0개 | 39개 / ~5초(LLM 호출 없음) |

## 포트폴리오/이력서용 한 줄 요약 (바로 쓸 수 있게)

- "LangGraph 기반 RAG 에이전트의 retrieve→generate→validate→retry 루프를 설계하고,
  LLM 출력을 결정론적 규칙으로 재검증해 평가 통과율을 70.8%→95.8%로 끌어올림"
- "구조화 로깅(trace_id 기반)과 토큰/비용 추적을 자체 구축해, 재시도율 개선이 비용
  절감으로 이어지는 것을 수치로 증명(24건당 $0.0134)"
- "단위 테스트 39개, 지수 백오프 재시도, 결과 캐싱을 추가해 단일 데모 코드를 신뢰성 있는
  서비스로 전환 — 캐시 히트 시 비용 $0, 응답 0초"
- "FastAPI 백엔드를 SQLite(로컬)와 PostgreSQL(배포) 양쪽에서 동작하도록 설계하고,
  Render 무료 티어에 직접 배포 — 배포 환경의 휘발성 파일시스템 제약을 파악해 FAISS
  인덱스를 정적 자산으로 git에 커밋하는 방식으로 콜드스타트 비용 제거"
- "웹 데모로 API 계약을 먼저 검증한 뒤 React Native(Expo) 모바일 앱에 동일 백엔드를
  연동, 실제 iPhone에서 Expo Go로 동작 확인"

## Phase별 타임라인 (자세한 내용은 [`README.md`](README.md)의 같은 제목 섹션 참고)

1. **평가(Evaluation) 파이프라인** — README "Phase 1" · [방법론](naengchae-langchain/eval/README.md)
2. **Observability** — README "Phase 2" · [스키마](naengchae-langchain/observability/README.md)
3. **RAG 코퍼스 확장 + Retrieval 평가** — README "Phase 3" · [방법론](naengchae-langchain/eval/RETRIEVAL_EVAL.md)
4. **백엔드 영속화 + 모바일 연동(4-1~4-5)** — README "Phase 4-1"~"Phase 4-5" (웹 우선 검증 →
   실사용 피드백 4건 → 유통기한 UX 단순화 → 모바일 포팅 → 실기기 테스트)
5. **신뢰성 강화** — README "Phase 5"
6. **배포 + 데모 자료** — README "Phase 6"

## 가장 "왜?"가 잘 드러나는 의사결정 3가지 (인터뷰/자기소개서용)

1. **검증 로직과 지식베이스의 모순 발견** (Phase 1) — 전자레인지 환경에서 "찜" 조리법을
   금지하는 코드가 있었는데, RAG 지식베이스는 정작 전자레인지에 계란찜을 추천하라고
   명시하고 있었다. 평가 하니스로 실패 케이스를 분석하다가 발견한, 두 컴포넌트 간
   암묵적 가정 불일치 버그. → [`docs/portfolio/bugfix_before_after_recipe_quantity.md`](docs/portfolio/bugfix_before_after_recipe_quantity.md)는
   비슷한 패턴의 또 다른 사례(재료 수량 기능)를 실제 git diff로 보여줍니다.
2. **무료 배포 환경의 제약을 파악하고 아키텍처를 조정** (Phase 6) — Render 무료 웹
   서비스의 파일시스템이 휘발성이라는 걸 미리 조사해서, SQLite 그대로 배포했다면
   재시작마다 데이터가 사라졌을 문제를 배포 전에 막음. PostgreSQL로 전환했지만 이번엔
   무료 DB도 30일 후 만료된다는 걸 발견해 README에 명시.
3. **평가 하니스의 무결성을 지키기 위해 캐싱을 기본 비활성으로 설계** (Phase 5) — 캐싱
   기능 자체는 비용을 줄이지만, `eval/run_eval.py`가 캐시를 쓰면 반복 실행 시 LLM을
   다시 안 부르고 과거 답만 돌려줘서 "평가"라는 목적이 무의미해진다는 걸 미리 인지하고
   opt-in으로 설계.

## 캡처/시각 자료

- [`docs/portfolio/eval_pass_rate_chart.png`](docs/portfolio/eval_pass_rate_chart.png) — 평가 통과율 차트(실측 데이터)
- [`docs/portfolio/observability_trace_example.md`](docs/portfolio/observability_trace_example.md) — 재시도→통과 실제 로그 트레이스
- [`docs/portfolio/bugfix_before_after_recipe_quantity.md`](docs/portfolio/bugfix_before_after_recipe_quantity.md) — 실제 git diff
- [`docs/portfolio/screenshot_checklist.md`](docs/portfolio/screenshot_checklist.md) — 직접 캡처해야 할 화면 목록(앱 실행 화면 등)
