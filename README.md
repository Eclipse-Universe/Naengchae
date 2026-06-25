# 냉채 (Naengchae)

냉장고에 있는 재료와 조리 환경(전자레인지만 / 가스레인지 1구 / 풀옵션)을 입력하면, RAG 기반
에이전트가 실제로 만들 수 있는 레시피 3개를 추천해주는 개인 사이드 프로젝트입니다.

부트캠프 Langchain 실습(팀 단위 과제)에서 한 단계 더 나아가, 결정론적 검증·재시도 루프를 가진
LangGraph 에이전트를 직접 설계하고, 합성 평가셋으로 성능을 측정·개선한 과정까지를 목표로
만들었습니다.

## 구조

```
naengchae-langchain/naengchae_chain/   # LangGraph RAG 에이전트 (핵심)
  ├─ models.py        # UserProfile / FridgeIngredient / Recipe / RecipeRecommendation (Pydantic)
  ├─ prompts.py        # 단순 체인용 + RAG/피드백 포함 에이전트용 프롬프트
  ├─ chain.py           # 단순 prompt | llm.with_structured_output 체인
  ├─ graph.py           # retrieve → generate → validate → retry(최대 2회) LangGraph
  └─ knowledge_base.py  # FAISS 기반 조리 지식 코퍼스
naengchae-langchain/eval/              # 평가 하니스 (Phase 1)
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

## Phase 1: 평가 하니스로 성능 측정·개선 (2026-06)

"에이전트를 만들었다"에서 멈추지 않고, 합성 테스트케이스 24건으로 통과율을 측정하고
실패를 분석해 실제로 개선했다는 것을 수치로 보였습니다. 자세한 방법론과 발견한 버그/수정 내역은
[`naengchae-langchain/eval/README.md`](naengchae-langchain/eval/README.md)에 있습니다.

| 지표 | 베이스라인 | 2회 개선 후 |
|---|---|---|
| 최종 통과율 | 70.8% | **91.7%** |
| 1차 통과율(재시도 없이) | 54.2% | **70.8%** |
| 평균 재시도 횟수 | 1.08 | **0.5** |

가장 영향이 컸던 발견: 검증 로직이 전자레인지 환경에서 "찜" 조리법을 금지하고 있었는데, 정작
RAG 지식베이스는 전자레인지에 계란찜·단호박찜이 적합하다고 명시하고 있어 둘이 서로 모순됐던
버그를 찾아 수정.

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

## 로드맵

1. ✅ 평가 하니스 구축 — 합성 테스트케이스로 통과율 측정 및 개선
2. ⬜ Observability — retrieve/generate/validate 구조화 로깅, 토큰/비용/지연시간 트래킹
3. ⬜ RAG 코퍼스 확장 + retrieval 품질 평가
4. ⬜ 백엔드 영속화(DB) + 모바일 화면 실제 구현·연동
5. ⬜ 신뢰성 강화 — 단위 테스트, LLM 실패 폴백, 캐싱
6. ⬜ 배포 + 데모 자료
