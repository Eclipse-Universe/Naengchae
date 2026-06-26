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

## Phase 4-2: 웹 데모 실사용 피드백 반영 (2026-06)

웹 데모를 실제로 써보면서 발견한 4가지 문제를 모바일로 넘어가기 전에 고쳤습니다 — 같은
문제를 Expo에서 또 발견했다면 디버깅 주기가 훨씬 길었을 것입니다. 자세한 원인 분석과 결정
과정은 `docs/ENGINEERING_LOG.md`의 "Phase 4-2"에 있습니다.

- 유통기한 입력란에 "구매일이 아니라 먹어야 하는 날짜"라는 설명 추가
- 추가 버튼이 마우스 위치에 따라 안 눌리던 문제 — 원인은 좁은 카드 너비에서 재료명/날짜/버튼
  3개를 한 줄에 욱여넣어 날짜 input의 캘린더 아이콘 영역이 버튼과 겹친 것. 입력란을 2줄로
  분리해 해결
- "1인 가구/핵가족" 두 칩 선택 대신 가구원 수를 직접 입력하도록 변경(2~3인 가구가 애매했던
  문제 해결), `householdType`은 가구원 수에서 자동 계산
- **레시피에 재료 수량 개념을 새로 추가**: `Recipe.usedIngredients`/`missingIngredients`가
  단순 이름 목록(`list[str]`)이었던 걸 `{name, amount, perServingAmount}` 구조로 바꾸고,
  `servings`가 항상 가구원 수와 같아야 한다는 검증을 코드로 추가(LLM 주장을 그대로 믿지 않고
  재확인하는 이 프로젝트의 핵심 패턴을 새 필드에도 적용). `memberCount=4`로 호출 시 계란
  `amount=4개`/`perServingAmount=1개`처럼 정확한 배수 관계로 나오는 것을 확인했습니다.

## Phase 4-3: 유통기한 입력을 "임박 여부" 토글로 단순화 (2026-06)

대부분의 사용자가 재료의 정확한 소비기한을 모른다는 점을 반영해, 기본 입력을 정확한 날짜
대신 "🔥 곧 먹어야 해요" 토글로 바꿨습니다. 토글을 켜면 내부적으로 오늘 날짜를 채워 넣어
기존 D+n 배지·검증 로직을 그대로 재사용합니다(백엔드 변경 없음). 정확한 날짜를 아는 경우를
위한 선택적 입력칸도 접어서 남겨뒀습니다. 자세한 트레이드오프 검토는
`docs/ENGINEERING_LOG.md`의 "Phase 4-3"에 있습니다.

## Phase 4-4: 모바일 FridgeScreen/RecipeScreen 연동 (2026-06)

웹에서 검증한 API(`/fridge`, `/profile`, `/recommend`)를 그대로 모바일 화면에 연동했습니다.
원래 계획은 하드코딩 레시피 10개였지만, 그 사이 백엔드가 완성됐으므로 실제 API 연동으로
범위를 키웠습니다. API 주소는 기기/에뮬레이터마다 다르므로(`EXPO_PUBLIC_API_URL` 환경변수,
`.env.example` 참고) 코드에 고정하지 않았고, 온보딩의 1인가구/핵가족 칩 모호함 문제(Phase
4-2와 동일한 버그)도 모바일에서 같이 고쳤습니다. 자세한 결정 이유는
`docs/ENGINEERING_LOG.md`의 "Phase 4-4"에 있습니다.

이 샌드박스에는 기기/에뮬레이터가 없어 실제 화면 동작은 직접 확인하지 못했습니다 — 대신
Node.js를 설치해 `npm install` 후 `npx expo export`로 앱 전체(928 모듈)를 실제 Metro로
번들링해 빌드 가능함을 확인했습니다. 실기기/에뮬레이터 테스트는 `EXPO_PUBLIC_API_URL`을
본인 환경에 맞게 설정한 뒤 직접 진행해야 합니다.

## Phase 4-5: 실기기(iPhone) 연동 — 네트워크 터널 + SDK 다운그레이드 (2026-06)

실제 iPhone의 Expo Go로 접속을 시도하면서 두 가지를 해결했습니다. (1) 개발 환경이 휴대폰과
다른 네트워크라 LAN IP 방식이 안 돼서, 백엔드(Cloudflare Quick Tunnel)와 Metro 개발 서버
(`expo start --tunnel`)에 각각 별도 터널을 만들었습니다. (2) 2026년 5월부터 앱스토어의
Expo Go 심사가 지연돼 스토어 버전이 SDK 54에 멈춰 있어, SDK 56으로 만든 프로젝트가
호환되지 않았습니다 — 유료 Apple Developer 계정 없이 바로 테스트할 수 있는 방법으로
프로젝트의 Expo SDK를 54로 다운그레이드했습니다(`npx expo install --fix` + `expo-doctor`
18/18 통과 확인). 자세한 과정은 `docs/ENGINEERING_LOG.md`의 "Phase 4-5"에 있습니다.

## Phase 5: 신뢰성 강화 — 단위 테스트, LLM 실패 폴백, 캐싱 (2026-06)

- **단위 테스트**: 핵심 검증 로직(`validate_recommendation`)을 LangGraph 클로저 밖으로
  꺼내 LLM 없이 테스트 가능하게 만들고, Phase 1의 회귀 버그를 포함한 39개 테스트
  추가(`naengchae-langchain/tests/`) — 전부 LLM 호출 없이 5초 안에 통과
- **LLM 실패 폴백**: `tenacity`로 LLM/임베딩 호출을 지수 백오프 재시도(최대 3회)하고,
  그래도 실패하면 `LLMUnavailableError`로 감싸 API가 503("잠시 후 다시 시도")으로
  깔끔하게 응답하도록 함(기존엔 SDK 내부 예외가 그대로 500으로 노출됐음)
- **캐싱**: 같은 (프로필, 재료, 날짜) 조합 재요청 시 LLM을 다시 안 부르고 캐시된 결과
  반환. 평가 하니스가 무의미해지지 않도록 기본은 꺼두고 웹 API에서만 켬. 실제 호출로
  확인: 1차 6.04초(LLM 3회 재시도) → 2차 0.00초(캐시 히트, 비용 $0)

자세한 결정 이유는 `docs/ENGINEERING_LOG.md`의 "Phase 5"에 있습니다.

## Phase 6: 배포 + 데모 자료 (2026-06)

- **DB를 PostgreSQL도 지원하도록 확장** (`naengchae_chain/db.py`): `DATABASE_URL` 환경변수가
  있으면 그걸 쓰고, 없으면 기존 SQLite로 동작 — 로컬 개발은 그대로, 배포 시에만 전환.
  Render의 무료 웹 서비스는 파일시스템이 재시작마다 초기화돼서 SQLite로 배포하면
  데이터가 사라지기 때문. 테스트 중 한글 INSERT가 깨지는 인코딩 문제를 발견해
  `client_encoding=utf8`을 명시하는 방어 코드 추가
- **FAISS 인덱스를 디스크에 캐싱** (`naengchae_chain/knowledge_base.py`): 코퍼스(94개
  문서)를 매번 재임베딩하면 콜드스타트마다 임베딩 API를 94번 호출하게 됨 — 인덱스를
  `faiss_index/`에 저장해 git에 커밋, 콜드스타트 시 이걸 로드해서 비용/지연 제거
- **`render.yaml`**: 웹 서비스(무료) + PostgreSQL(무료)을 한 번에 정의하는 Render
  Blueprint. `UPSTAGE_API_KEY`는 비밀값이라 파일에 안 넣고 대시보드에서 직접 입력
- **실제 배포 단계** (계정 생성이 필요해 사용자가 직접 해야 함):
  1. [render.com](https://render.com)에서 무료 계정 생성(카드 불필요)
  2. 대시보드에서 "New" → "Blueprint" → 이 GitHub 저장소 연결 → `render.yaml` 자동 인식
  3. 생성된 웹 서비스의 Environment 설정에서 `UPSTAGE_API_KEY`를 본인 키로 입력
  4. 배포 완료 후 `https://<서비스이름>.onrender.com`으로 접속 확인

자세한 결정 이유는 `docs/ENGINEERING_LOG.md`의 "Phase 6"에 있습니다.

## 실행 방법

### 평가 하니스
```bash
cd naengchae-langchain
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "UPSTAGE_API_KEY=..." > .env
python3 eval/run_eval.py
```

### 단위 테스트 (LLM 호출 없음, API 키 불필요)
```bash
cd naengchae-langchain
source .venv/bin/activate
python3 -m pytest tests/ -v
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
cp .env.example .env.local   # EXPO_PUBLIC_API_URL을 본인 실행 환경(시뮬레이터/에뮬레이터/실기기)에 맞게 수정
npx expo start
```

## 로드맵 (MLOps/LLMOps 파이프라인 → 실제 애플리케이션)

1. ✅ 평가(Evaluation) 파이프라인 — 합성 테스트케이스로 통과율 측정 및 개선
2. ✅ Observability — retrieve/generate/validate 구조화 로깅, 토큰/비용/지연시간 트래킹
3. ✅ RAG 코퍼스 확장 + retrieval 품질 평가
4. ✅ 백엔드 영속화(DB) + 모바일 화면 실제 구현·연동 — 백엔드+웹+실기기(iPhone) 검증 완료.
   ReportScreen(재료 활용률 등)은 추천 히스토리 기록이 더 필요해 별도 작업으로 분리
5. ✅ 신뢰성 강화 — 단위 테스트(39개), LLM 실패 폴백(재시도+503), 캐싱
6. 🟡 배포 + 데모 자료 — 배포 설정(render.yaml, Postgres 지원, FAISS 캐싱) 완료, 실제
   계정 생성·배포는 사용자 진행 필요. 데모 자료(`docs/portfolio/`)는 준비 완료

각 단계에서 만난 문제와 해결 전략은 [`docs/ENGINEERING_LOG.md`](docs/ENGINEERING_LOG.md)에 계속
누적해서 기록합니다.
