# 냉채 레시피 추천 에이전트입니다.
# LangGraph StateGraph로 retrieve(RAG 검색) -> generate(레시피 생성)
# -> validate(제약 검증) -> (필요시 generate로 재시도) 루프를 구성합니다.
#
# /root/Langchain의 06-final_exercise 노트북에서 사용한
# "갈래길(재시도 횟수 제한) + 조건부 라우징" 패턴을 따릅니다.

from datetime import date
from typing import Optional, TypedDict

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from langchain_core.vectorstores import VectorStoreRetriever
from langgraph.graph import END, START, StateGraph

from .chain import EXPIRY_WARNING_DAYS, _format_ingredients
from .models import FridgeIngredient, RecipeRecommendation, UserProfile
from .prompts import recipe_agent_prompt

MAX_RETRIES = 2
RECURSION_LIMIT = 10

# prompts.py Rule 2와 동일한 목록. validate에서 기본 조미료는 usedIngredients 검사를 건너뜁니다.
BASIC_SEASONINGS: frozenset[str] = frozenset([
    "소금", "설탕", "후추", "식용유", "간장", "고추장", "된장",
    "참기름", "마늘", "고춧가루", "물",
])

# 조리환경에서 사용할 수 없는 조리 방식 키워드.
# 레시피의 이름/태그/조리 순서에 이 키워드가 등장하면 validate 단계에서 문제로 표시합니다.
ENV_FORBIDDEN_KEYWORDS: dict[str, list[str]] = {
    "microwave": ["오븐", "에어프라이어", "가스레인지", "프라이팬", "직화", "팬"],
    "oneburner": ["오븐", "에어프라이어", "전자레인지"],
    "full": [],
}


class RecipeAgentState(TypedDict):
    """레시피 추천 에이전트의 공유 상태."""

    profile: UserProfile
    ingredients: list[FridgeIngredient]
    ingredients_text: str
    expiring_ingredients_text: str
    expiring_names: list[str]
    retrieved_context: str
    recommendation: Optional[RecipeRecommendation]
    feedback: str
    retry_count: int
    valid: bool


def _expiring_names(ingredients: list[FridgeIngredient], today: date) -> list[str]:
    """유통기한이 임박한 재료의 이름 목록을 반환합니다."""
    names = []
    for ingredient in ingredients:
        if ingredient.expiryDate is None:
            continue
        expiry = date.fromisoformat(ingredient.expiryDate)
        if (expiry - today).days <= EXPIRY_WARNING_DAYS:
            names.append(ingredient.name)
    return names


def _format_docs(docs: list[Document]) -> str:
    if not docs:
        return "(참고 자료 없음)"
    return "\n\n".join(f"- {doc.page_content}" for doc in docs)


def _ingredient_match(name: str, candidates: list[str]) -> bool:
    """이름이 candidates 중 하나와 겹치는지(부분 일치 포함) 확인합니다."""
    target = name.replace(" ", "")
    for candidate in candidates:
        candidate_norm = candidate.replace(" ", "")
        if target in candidate_norm or candidate_norm in target:
            return True
    return False


def _ingredient_match_any(used_ingredients: list[str], names: list[str]) -> bool:
    return any(_ingredient_match(used, names) for used in used_ingredients)


def build_recipe_agent_graph(
    llm: BaseChatModel, retriever: VectorStoreRetriever
) -> Runnable:
    """retrieve -> generate -> validate -> (재시도 or 종료) 그래프를 컴파일합니다."""

    generate_chain = recipe_agent_prompt | llm.with_structured_output(RecipeRecommendation)

    def retrieve_node(state: RecipeAgentState) -> dict:
        profile = state["profile"]
        query = (
            f"보유 재료: {state['ingredients_text']}\n"
            f"조리 환경: {profile.cookingEnv}\n"
            f"음식 취향: {', '.join(profile.foodPreference)}\n"
            f"유통기한 임박 재료: {', '.join(state['expiring_names']) or '없음'}"
        )
        docs = retriever.invoke(query)
        return {"retrieved_context": _format_docs(docs)}

    def generate_node(state: RecipeAgentState) -> dict:
        profile = state["profile"]
        feedback = state["feedback"]
        feedback_section = (
            f"\n[이전 추천의 문제점 - 반드시 수정하세요]\n{feedback}\n" if feedback else ""
        )
        result = generate_chain.invoke(
            {
                "householdType": profile.householdType,
                "memberCount": profile.memberCount,
                "cookingEnv": profile.cookingEnv,
                "foodPreference": profile.foodPreference,
                "ingredients_text": state["ingredients_text"],
                "expiring_ingredients_text": state["expiring_ingredients_text"],
                "retrieved_context": state["retrieved_context"],
                "feedback_section": feedback_section,
            }
        )
        return {"recommendation": result}

    def validate_node(state: RecipeAgentState) -> dict:
        recommendation = state["recommendation"]
        cooking_env = state["profile"].cookingEnv
        fridge_names = [ingredient.name for ingredient in state["ingredients"]]
        expiring_names = state["expiring_names"]
        forbidden_keywords = ENV_FORBIDDEN_KEYWORDS.get(cooking_env, [])

        issues: list[str] = []
        used_expiring = False

        for i, recipe in enumerate(recommendation.recipes, start=1):
            recipe_text = " ".join([recipe.name, *recipe.tags, *recipe.steps])

            for keyword in forbidden_keywords:
                if keyword in recipe_text:
                    issues.append(
                        f"레시피 {i}({recipe.name}): '{cooking_env}' 환경에서는 "
                        f"'{keyword}'을 사용하는 조리법을 추천할 수 없습니다."
                    )
                    break

            for used in recipe.usedIngredients:
                if used in BASIC_SEASONINGS:
                    continue  # 기본 조미료는 항상 보유 가정
                if not _ingredient_match(used, fridge_names):
                    issues.append(
                        f"레시피 {i}({recipe.name}): usedIngredients의 '{used}'가 "
                        "보유 재료 목록에 없습니다."
                    )

            if recipe.usesExpiringIngredient:
                if _ingredient_match_any(recipe.usedIngredients, expiring_names):
                    used_expiring = True
                else:
                    issues.append(
                        f"레시피 {i}({recipe.name}): usesExpiringIngredient가 true이지만 "
                        "유통기한 임박 재료를 실제로 사용하지 않았습니다."
                    )

        if expiring_names and not used_expiring:
            issues.append(
                f"유통기한 임박 재료({', '.join(expiring_names)})를 사용하는 레시피가 "
                "하나도 없습니다."
            )

        valid = len(issues) == 0
        retry_count = state["retry_count"] + (0 if valid else 1)
        return {"valid": valid, "feedback": "\n".join(issues), "retry_count": retry_count}

    def route_after_validate(state: RecipeAgentState) -> str:
        if state["valid"] or state["retry_count"] > MAX_RETRIES:
            return END
        return "generate"

    builder = StateGraph(RecipeAgentState)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("generate", generate_node)
    builder.add_node("validate", validate_node)

    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "generate")
    builder.add_edge("generate", "validate")
    builder.add_conditional_edges(
        "validate", route_after_validate, {"generate": "generate", END: END}
    )

    return builder.compile()


def recommend_recipes_agent(
    llm: BaseChatModel,
    retriever: VectorStoreRetriever,
    profile: UserProfile,
    ingredients: list[FridgeIngredient],
    today: date | None = None,
) -> tuple[RecipeRecommendation, RecipeAgentState]:
    """RAG + 검증/재시도 루프를 거쳐 레시피 3개를 추천합니다.

    반환값: (최종 추천 결과, 최종 상태) - 상태에는 검증 결과(valid, feedback,
    retry_count)와 검색된 참고 자료(retrieved_context)가 포함되어 디버깅에 사용할 수 있습니다.
    """
    today = today or date.today()
    graph = build_recipe_agent_graph(llm, retriever)

    ingredients_text, expiring_ingredients_text = _format_ingredients(ingredients, today)

    initial_state: RecipeAgentState = {
        "profile": profile,
        "ingredients": ingredients,
        "ingredients_text": ingredients_text,
        "expiring_ingredients_text": expiring_ingredients_text,
        "expiring_names": _expiring_names(ingredients, today),
        "retrieved_context": "",
        "recommendation": None,
        "feedback": "",
        "retry_count": 0,
        "valid": False,
    }

    final_state = graph.invoke(initial_state, config={"recursion_limit": RECURSION_LIMIT})
    return final_state["recommendation"], final_state
