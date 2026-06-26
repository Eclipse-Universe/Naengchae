# 냉채 레시피 추천 체인에서 사용하는 데이터 구조(Pydantic 모델) 모음입니다.
# - UserProfile / FridgeIngredient: 체인의 "입력"으로 들어가는 데이터
#   (Expo 앱의 AsyncStorage에 저장된 userProfile, 냉장고 재료 목록과 동일한 필드명을 사용합니다)
# - Recipe / RecipeRecommendation: LLM이 with_structured_output으로 "출력"해야 하는 데이터

from typing import Literal, Optional

from pydantic import BaseModel, Field

HouseholdType = Literal["single", "family"]
CookingEnv = Literal["microwave", "oneburner", "full"]
FoodPreference = Literal["korean", "western", "japanese", "highprotein", "none"]


class UserProfile(BaseModel):
    """온보딩에서 저장된 사용자 프로필 (앱의 userProfile과 동일한 필드)."""

    householdType: HouseholdType
    memberCount: int = Field(ge=1, le=5, description="가구원 수 (5는 '5명 이상'의 의미)")
    cookingEnv: CookingEnv
    foodPreference: list[FoodPreference]


class FridgeIngredient(BaseModel):
    """냉장고 탭에 등록된 재료 1개."""

    name: str
    expiryDate: Optional[str] = Field(
        default=None, description="유통기한, 'YYYY-MM-DD' 형식. 없으면 None"
    )


class UsedIngredient(BaseModel):
    """레시피에서 실제로 사용하는 보유 재료 1개와 수량."""

    name: str = Field(description="재료 이름 (보유 재료 목록에 있는 이름과 일치해야 함)")
    amount: str = Field(
        description="이 레시피의 servings 인분 기준 수량. 예: '1모', '200g', '2개'"
    )
    perServingAmount: str = Field(
        description="amount를 1인분 기준으로 환산한 수량. 예: amount가 4인분 기준 '2개'라면 "
                    "perServingAmount는 '0.5개'"
    )


class MissingIngredient(BaseModel):
    """레시피에 추가로 필요한, 보유하지 않은 재료 1개와 수량."""

    name: str = Field(description="재료 이름")
    amount: str = Field(description="이 레시피의 servings 인분 기준으로 필요한 수량")


class Recipe(BaseModel):
    """LLM이 추천하는 레시피 1개."""

    name: str = Field(description="레시피 이름")
    cookingTime: int = Field(description="예상 조리 시간 (분)")
    servings: int = Field(description="몇 인분 기준인지. 사용자의 memberCount와 동일해야 함")
    usedIngredients: list[UsedIngredient] = Field(
        description="사용자의 냉장고 보유 재료 목록에 있는 항목 중 이 레시피에서 사용하는 것만 포함. "
                    "소금·설탕·간장 등 기본 조미료는 물론 절대 포함하지 않음."
    )
    missingIngredients: list[MissingIngredient] = Field(
        default_factory=list, description="추가로 필요한 재료 목록 (없으면 빈 리스트)"
    )
    tags: list[str] = Field(
        default_factory=list, description="예: '한식', '간단요리', '에어프라이어' 등"
    )
    steps: list[str] = Field(description="조리 순서 (단계별 설명)")
    usesExpiringIngredient: bool = Field(
        description="유통기한이 임박한 재료를 사용하는 레시피인지 여부"
    )


class RecipeRecommendation(BaseModel):
    """레시피 추천 체인의 최종 출력. 항상 레시피 3개를 담습니다."""

    recipes: list[Recipe] = Field(description="추천 레시피 3개")
