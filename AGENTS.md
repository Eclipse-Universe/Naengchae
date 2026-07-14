# 프로젝트 컨텍스트 (Claude / AI 에이전트용)

## 한 줄 요약
냉장고 재료 + 조리환경 → LangGraph RAG 에이전트 → 레시피 3개 추천.
MLOps/LLMOps 파이프라인(평가→관찰성→신뢰성→배포)을 직접 구축하고 모바일+백엔드+배포까지
이어지는 실제 동작 앱으로 완성하는 게 목표인 개인 포트폴리오 프로젝트.

## 저장소 구조
```
naengchae-langchain/naengchae_chain/   핵심 AI 에이전트 패키지 (Python)
  models.py           Pydantic 데이터 모델 (UserProfile, FridgeIngredient, Recipe 등)
  prompts.py          LLM 프롬프트
  chain.py            단순 체인 (RAG 없음, 참고용)
  graph.py            실제 에이전트: retrieve→generate→validate→retry(최대 2회) LangGraph
  knowledge_base.py   FAISS 기반 조리 지식 코퍼스 (94개 문서), 디스크 캐시 지원
  observability.py    JSON Lines 구조화 로깅, 토큰/비용 추적
  db.py               SQLite(로컬) / PostgreSQL(배포) 영속 계층 — DATABASE_URL 분기
  cache.py            SHA256 키 인메모리 캐시 (웹 API만 활성화, eval은 비활성)
  errors.py           LLMUnavailableError 공용 예외
naengchae-langchain/eval/              평가 하니스 (24개 합성 케이스, run_eval.py)
naengchae-langchain/tests/             단위 테스트 39개 (LLM 없이 ~5초)
naengchae-langchain/faiss_index/       FAISS 인덱스 (git 커밋된 정적 자산, 재임베딩 불필요)
web/                                   FastAPI 데모 서버 + 웹 UI
  main.py             API 엔드포인트 (/fridge, /profile, /recommend)
  static/index.html   브라우저 데모 화면
src/                                   Expo(React Native) 모바일 앱
  screens/FridgeScreen.js   냉장고 재료 관리
  screens/RecipeScreen.js   레시피 추천
  screens/onboarding/       온보딩 (가구원수·조리환경·취향 설정)
docs/ENGINEERING_LOG.md                전체 의사결정 + 문제 해결 기록 (세션 간 인수인계용)
PORTFOLIO.md                           포트폴리오 작성용 단일 요약 문서
```

## 기술 스택
- LLM: Upstage `solar-pro3` (chat), `solar-embedding-1-large` (embedding)
- Agent: LangGraph StateGraph
- RAG: FAISS vectorstore
- Backend: FastAPI + SQLModel (SQLite/PostgreSQL 겸용)
- Mobile: Expo SDK **54** (v54 — NOT v56, App Store Expo Go 심사 지연으로 v54에 고정됨)
- 배포: Render (무료 웹서비스 + 무료 PostgreSQL)
- 테스트: pytest 39개
- 재시도: tenacity (지수 백오프, 3회)

## Expo 관련 주의사항
**Expo SDK 버전은 54입니다 (56 아님).**
App Store의 Expo Go 심사 지연으로 2026년 5월 기준 스토어판 Expo Go가 SDK 54에
멈춰 있어 v54로 다운그레이드했습니다. Expo 관련 코드를 수정할 때는
https://docs.expo.dev/versions/v54.0.0/ 을 참고하세요.

## 핵심 설계 패턴 (코드 수정 시 반드시 유지)
1. **LLM 출력을 결정론적 코드로 재검증** — `graph.py`의 `validate_recommendation()`이
   핵심. LLM이 뭐라고 해도 조리환경 호환성, 보유 재료 여부, servings==memberCount 등을
   코드로 재확인한다. 이 검증을 우회하거나 약화시키면 안 됨.
2. **캐시는 eval에서 비활성** — `recommend_recipes_agent(use_cache=False)` 기본값.
   웹 API에서만 `use_cache=True`. 평가 하니스가 캐시된 답을 돌려주면 평가 의미가 없기 때문.
3. **단일 사용자 가정** — `db.py`의 `UserProfileRow`는 항상 `id=1` 단일 행. 인증/멀티유저는
   별도 작업으로 명시적으로 제외된 범위.

## 배포 환경
- 라이브 URL: https://naengchae-web.onrender.com/
- 환경변수: `DATABASE_URL`(Render가 자동 주입), `UPSTAGE_API_KEY`(대시보드에서 수동 입력)
- ⚠️ 무료 PostgreSQL은 생성 후 30일+14일 유예 뒤 만료됨 (코드/서비스는 유지, 데이터만 삭제)

## 로컬 실행
```bash
# 에이전트 패키지 + 웹 서버
cd naengchae-langchain
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "UPSTAGE_API_KEY=sk-..." > .env
cd ../web && uvicorn main:app --reload   # http://localhost:8000

# 단위 테스트 (API 키 불필요)
cd naengchae-langchain && python3 -m pytest tests/ -v

# 모바일
npm install
cp .env.example .env.local   # EXPO_PUBLIC_API_URL 수정
npx expo start
```

## 전체 진행 기록
의사결정 이유, 발견한 버그, 해결 전략은 전부 `docs/ENGINEERING_LOG.md`에 기록돼 있음.
새 세션이 열리면 이 파일을 먼저 읽으면 맥락을 바로 잡을 수 있음.
