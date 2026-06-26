# 포트폴리오용 캡처: 문제→진단→수정 한 쌍 (재료 수량 기능)

이 프로젝트의 차별점은 "기능을 만들었다"가 아니라 "왜 그렇게 만들었는지"입니다.
아래는 사용자 피드백 한 문장이 실제 코드 변경으로 이어진 과정의 실제 git diff입니다
(가공하지 않은 실제 커밋: `81e53c6`).

## 1. 발견 (사용자 피드백, 가공 없이 그대로)

> "이 인원에 맞춰서 레시피도 비례하게 양을 맞추는 게 좋아 보여. 4인분 기준으로 레시피를
> 추천해준다고 하면, 옆에 따로 1인분 기준도 만들어 놓으면 알아보기 쉽고 조절하기 용이할
> 것 같아."

## 2. 진단

코드를 보니 `Recipe.usedIngredients`/`missingIngredients`가 재료 **이름만** 담는
`list[str]`이었다 — 수량 자체가 데이터 구조에 없어서 "인원수에 비례한 분량"이라는 개념을
표현할 방법이 애초에 없었다. UI 문제가 아니라 데이터 모델 문제였다.

## 3. 수정 (`naengchae_chain/models.py`, 실제 diff)

```diff
+class UsedIngredient(BaseModel):
+    """레시피에서 실제로 사용하는 보유 재료 1개와 수량."""
+
+    name: str = Field(description="재료 이름 (보유 재료 목록에 있는 이름과 일치해야 함)")
+    amount: str = Field(
+        description="이 레시피의 servings 인분 기준 수량. 예: '1모', '200g', '2개'"
+    )
+    perServingAmount: str = Field(
+        description="amount를 1인분 기준으로 환산한 수량. 예: amount가 4인분 기준 '2개'라면 "
+                    "perServingAmount는 '0.5개'"
+    )
+
+
+class MissingIngredient(BaseModel):
+    """레시피에 추가로 필요한, 보유하지 않은 재료 1개와 수량."""
+
+    name: str = Field(description="재료 이름")
+    amount: str = Field(description="이 레시피의 servings 인분 기준으로 필요한 수량")


 class Recipe(BaseModel):
     name: str = Field(description="레시피 이름")
     cookingTime: int = Field(description="예상 조리 시간 (분)")
-    servings: int = Field(description="몇 인분 기준인지")
-    usedIngredients: list[str] = Field(...)
-    missingIngredients: list[str] = Field(...)
+    servings: int = Field(description="몇 인분 기준인지. 사용자의 memberCount와 동일해야 함")
+    usedIngredients: list[UsedIngredient] = Field(...)
+    missingIngredients: list[MissingIngredient] = Field(...)
```

같이 한 일(코드만으로는 안 보이는 부분):
- `graph.py`의 `_validate`에 `recipe.servings != member_count`면 검증 실패로 잡는 로직을
  추가 — "LLM이 4인분이라고 말했다"를 믿지 않고 실제로 가구원 수와 일치하는지 코드로 재확인.
- 1차 테스트에서 "김치 1/4모"(모=두부 단위, 김치엔 안 맞음) 같은 단위 오류를 발견해서
  프롬프트에 한 줄 더 추가해 재검증.

## 4. 결과 (실제 API 응답, `memberCount=4`)

```
계란말이 | servings=4
  used: 계란 amount=4개 perServing=1개
  used: 김치 amount=200g perServing=50g
```

## 캡처 방법 제안
- 위 diff를 GitHub의 커밋 `81e53c6` 페이지에서 캡처(문법 강조가 자동으로 입혀짐)하거나,
  VS Code의 git diff 뷰에서 캡처
- "전" 스크린샷으로 4-1 단계 결과(이름만 있는 재료 목록)와 "후" 스크린샷으로 4-2 이후
  결과(수량 포함)를 나란히 놓으면 더 효과적
