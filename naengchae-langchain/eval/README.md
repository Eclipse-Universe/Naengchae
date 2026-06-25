# 냉채 레시피 추천 에이전트 평가 (Phase 1)

`naengchae_chain.graph.recommend_recipes_agent`(retrieve → generate → validate → retry 루프)가
실제로 얼마나 잘 동작하는지 합성 테스트케이스로 측정하고, 발견된 문제를 고친 전/후 수치를 비교한다.

## 방법론

- `cases.json`: 24개 합성 테스트케이스. `cookingEnv`(microwave/oneburner/full) × `foodPreference`
  × `householdType`/`memberCount` 조합에, 유통기한 임박/만료/없음, 빈 냉장고, 지식베이스에 없는
  재료, 재료 이름 표기 변형 등 edge case를 더해 구성했다.
- `run_eval.py`: 각 케이스에 대해 `recommend_recipes_agent`를 실제 LLM(Upstage `solar-pro3`)으로
  호출하고, 최종 `valid`/`retry_count`/`feedback`/응답 시간을 기록한다. `validate_node`가 남긴
  실패 사유 문자열을 정규식으로 4가지 유형(`forbidden_cooking_method`, `ingredient_not_in_fridge`,
  `expiring_flag_false_positive`, `expiring_ingredient_unused`)으로 분류해 집계한다.
- 모든 케이스는 `today`를 고정해 유통기한 임박 판정이 재현 가능하도록 했다.

## 측정 지표

- **최종 통과율**: 최대 2회 재시도 후에도 `valid=True`인 케이스 비율
- **1차 통과율**: 재시도 없이 첫 생성에서 통과한 비율 (`retry_count == 0`)
- **평균 재시도 횟수** / 재시도 횟수 분포
- **실패 유형 분포**: 실패 케이스가 어떤 검증 규칙을 위반했는지
- **평균 응답 시간**

## 결과: 베이스라인 → 개선 2회

| 지표 | 베이스라인 | 1차 개선 | 2차 개선 |
|---|---|---|---|
| 최종 통과율 | 70.8% (17/24) | 79.2% (19/24) | **91.7% (22/24)** |
| 1차 통과율 | 54.2% | 62.5% | **70.8%** |
| 평균 재시도 횟수 | 1.08 | 0.83 | **0.5** |
| 평균 응답 시간 | 20.2s | 15.4s | 23.2s |

원시 결과: `results/run_20260625_144100.json`(베이스라인), `results/run_20260625_144835.json`(1차),
`results/run_20260625_153616.json`(2차).

### 발견한 문제와 수정

1. **검증기 버그 (가장 큰 영향)**: `graph.py`의 `ENV_FORBIDDEN_KEYWORDS["microwave"]`에 `"찜"`이
   금지 키워드로 들어 있었는데, RAG 지식베이스(`knowledge_base.py`)는 정작 "전자레인지 환경에서는
   계란찜·단호박찜이 적합하다"고 명시한다. 검증기와 지식이 서로 모순되어, LLM이 올바르게 추천해도
   매번 실패 판정을 받았다. `"찜"`을 금지 목록에서 제거 → microwave 케이스 4건 중 3건이 즉시 해결.
2. **암묵적 재료 가정**: 기본 조미료 10종 외에도 LLM이 밥(쌀밥)·김치처럼 "흔히 집에 있을 법한"
   재료를 [보유 재료] 목록에 없어도 사용한 것으로 처리하는 경향이 있었다. `prompts.py`에 구체적인
   금지 예시(김치찌개·볶음밥 등 핵심 재료가 없으면 추천하지 말 것)와 자기 검증 지시를 추가.
3. **유통기한 임박 플래그 오탐**: `usesExpiringIngredient=true`를 실제 사용 여부와 무관하게,
   또는 임박 재료가 하나도 없는데도 표시하는 경우가 있었다. "목록이 (없음)이면 무조건 false",
   "true로 표시하기 전 글자 그대로 포함되는지 재확인" 두 가지 명시적 규칙을 추가.

### 남은 실패 2건 (91.7%에서 멈춘 이유)

- `microwave_highprotein`, `korean_full_large_pantry`: 위 3번·2번 문제가 산발적으로 재발하는
  케이스. 같은 종류의 오류를 프롬프트 규칙만으로 100% 박멸하기는 어려운 구간으로 판단해 Phase 1은
  여기서 마무리했다. 다음 시도로는 few-shot 예시 추가, 또는 generate 직후 자기 검증
  (self-critique) 단계 도입을 고려할 수 있다.

## 실행 방법

```bash
cd naengchae-langchain
source .venv/bin/activate   # 최초 1회: python3 -m venv .venv && pip install -r requirements.txt
echo "UPSTAGE_API_KEY=..." > .env
python3 eval/run_eval.py
```

결과는 콘솔에 출력되고 `eval/results/run_<timestamp>.json`에 저장된다.
