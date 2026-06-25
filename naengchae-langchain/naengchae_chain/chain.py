# 냉채 레시피 추천 체인의 핵심 로직입니다.
# LLM은 외부에서 주입받습니다 (build_recipe_chain의 llm 인자).
# 어떤 LLM(OpenAI, Upstage 등)을 쓸지는 아직 결정되지 않았으므로,
# 이 모듈은 langchain_core의 BaseChatModel 인터페이스에만 의존합니다.

from datetime import date, datetime

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable

from .models import FridgeIngredient, RecipeRecommendation, UserProfile
from .prompts import recipe_prompt

EXPIRY_WARNING_DAYS = 3


def build_recipe_chain(llm: BaseChatModel) -> Runnable:
    """프롬프트 + 구조화 출력을 연결한 LCEL 체인을 만듭니다.

    /root/Langchain의 contract-analyzer / langsmith-eval 노트북에서 사용한
    `prompt | llm.with_structured_output(PydanticModel)` 패턴을 그대로 따릅니다.
    """
    return recipe_prompt | llm.with_structured_output(RecipeRecommendation)


def _format_ingredients(
    ingredients: list[FridgeIngredient], today: date
) -> tuple[str, str]:
    """보유 재료 목록을 프롬프트에 넣을 텍스트 두 개로 변환합니다.

    반환값: (전체 재료 목록 텍스트, 유통기한 임박 재료 목록 텍스트)
    """
    if not ingredients:
        return "(보유한 재료가 없습니다)", "(없음)"

    all_lines = []
    expiring_lines = []

    for ingredient in ingredients:
        if ingredient.expiryDate is None:
            all_lines.append(f"- {ingredient.name}")
            continue

        expiry = datetime.strptime(ingredient.expiryDate, "%Y-%m-%d").date()
        days_left = (expiry - today).days
        all_lines.append(f"- {ingredient.name} (유통기한: {ingredient.expiryDate})")

        if days_left <= EXPIRY_WARNING_DAYS:
            expiring_lines.append(f"- {ingredient.name} (D{days_left:+d})")

    ingredients_text = "\n".join(all_lines)
    expiring_text = "\n".join(expiring_lines) if expiring_lines else "(없음)"
    return ingredients_text, expiring_text


def recommend_recipes(
    llm: BaseChatModel,
    profile: UserProfile,
    ingredients: list[FridgeIngredient],
    today: date | None = None,
) -> RecipeRecommendation:
    """사용자 프로필 + 보유 재료를 받아 레시피 3개를 추천합니다."""
    chain = build_recipe_chain(llm)

    ingredients_text, expiring_ingredients_text = _format_ingredients(
        ingredients, today or date.today()
    )

    return chain.invoke(
        {
            "householdType": profile.householdType,
            "memberCount": profile.memberCount,
            "cookingEnv": profile.cookingEnv,
            "foodPreference": profile.foodPreference,
            "ingredients_text": ingredients_text,
            "expiring_ingredients_text": expiring_ingredients_text,
        }
    )
