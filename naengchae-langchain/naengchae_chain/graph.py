# 냉채 레시피 추천 에이전트입니다.
# LangGraph StateGraph로 retrieve(RAG 검색) -> generate(레시피 생성)
# -> validate(제약 검증) -> (필요시 generate로 재시도) 루프를 구성합니다.
#
# /root/Langchain의 06-final_exercise 노트북에서 사용한
# "갈래길(재시도 횟수 제한) + 조건부 라우징" 패턴을 따릅니다.

import uuid
from datetime import date
from typing import Any, Callable, Optional, TypedDict

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from langchain_core.vectorstores import VectorStoreRetriever
from langgraph.graph import END, START, StateGraph
from tenacity import retry, stop_after_attempt, wait_exponential

from . import cache
from .chain import EXPIRY_WARNING_DAYS, _format_ingredients
from .errors import LLMUnavailableError
from .models import FridgeIngredient, RecipeRecommendation, UsedIngredient, UserProfile
from .observability import extract_usage, log_event, summarize_usage, timed
from .prompts import recipe_agent_prompt

MAX_RETRIES = 2
RECURSION_LIMIT = 10
LLM_CALL_MAX_ATTEMPTS = 3


def invoke_with_retry(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """LLM 호출처럼 일시적으로 실패할 수 있는 작업을 지수 백오프로 재시도합니다.

    검증 실패(validate -> generate 재시도, MAX_RETRIES)와는 다른 종류의 실패입니다 —
    저건 "LLM이 답은 했는데 그 답이 우리 규칙에 안 맞는" 경우이고, 여기서 다루는 건
    "LLM 호출 자체가 네트워크/요금제한/타임아웃으로 실패한" 경우입니다. 모든 시도가
    실패하면 원본 예외를 LLMUnavailableError로 감싸서 올립니다 — 호출하는 쪽(API 서버
    등)이 SDK 내부 예외 타입을 몰라도 "LLM이 지금 안 된다"만 보고 깔끔하게 처리할 수
    있게 하기 위함입니다.
    """

    @retry(
        stop=stop_after_attempt(LLM_CALL_MAX_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _call() -> Any:
        return fn(*args, **kwargs)

    try:
        return _call()
    except Exception as e:
        raise LLMUnavailableError(
            f"LLM 호출이 {LLM_CALL_MAX_ATTEMPTS}번 재시도 후에도 실패했습니다: {e}"
        ) from e

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

    trace_id: str
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
    token_usage: list[dict]


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


def _ingredient_match_any(used_ingredients: list[UsedIngredient], names: list[str]) -> bool:
    return any(_ingredient_match(used.name, names) for used in used_ingredients)


def validate_recommendation(
    recommendation: RecipeRecommendation,
    cooking_env: str,
    member_count: int,
    fridge_names: list[str],
    expiring_names: list[str],
) -> list[str]:
    """추천 레시피 3개를 결정론적 규칙으로 검증하고, 문제점 목록(issues)을 반환합니다.

    원래 build_recipe_agent_graph 안에 닫힌 함수(_validate)였던 것을 모듈 최상위로
    뽑아냈습니다 — LangGraph state(TypedDict) 대신 평범한 파라미터를 받게 해서, LLM이나
    그래프를 띄우지 않고도 이 핵심 검증 로직만 단위 테스트할 수 있게 하는 게 목적입니다
    (tests/test_validate.py). 동작은 이전과 동일합니다.
    """
    forbidden_keywords = ENV_FORBIDDEN_KEYWORDS.get(cooking_env, [])

    issues: list[str] = []
    used_expiring = False

    for i, recipe in enumerate(recommendation.recipes, start=1):
        recipe_text = " ".join([recipe.name, *recipe.tags, *recipe.steps])

        if recipe.servings != member_count:
            issues.append(
                f"레시피 {i}({recipe.name}): servings가 {recipe.servings}인분인데 "
                f"사용자 가구원 수는 {member_count}명입니다. servings를 {member_count}로 "
                "맞추고 amount/perServingAmount도 그에 맞게 다시 계산하세요."
            )

        for keyword in forbidden_keywords:
            if keyword in recipe_text:
                issues.append(
                    f"레시피 {i}({recipe.name}): '{cooking_env}' 환경에서는 "
                    f"'{keyword}'을 사용하는 조리법을 추천할 수 없습니다."
                )
                break

        for used in recipe.usedIngredients:
            if used.name in BASIC_SEASONINGS:
                continue  # 기본 조미료는 항상 보유 가정
            if not _ingredient_match(used.name, fridge_names):
                issues.append(
                    f"레시피 {i}({recipe.name}): usedIngredients의 '{used.name}'가 "
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

    return issues


def build_recipe_agent_graph(
    llm: BaseChatModel, retriever: VectorStoreRetriever
) -> Runnable:
    """retrieve -> generate -> validate -> (재시도 or 종료) 그래프를 컴파일합니다."""

    model_name = getattr(llm, "model", "unknown")
    generate_chain = recipe_agent_prompt | llm.with_structured_output(
        RecipeRecommendation, include_raw=True
    )

    def retrieve_node(state: RecipeAgentState) -> dict:
        profile = state["profile"]
        query = (
            f"보유 재료: {state['ingredients_text']}\n"
            f"조리 환경: {profile.cookingEnv}\n"
            f"음식 취향: {', '.join(profile.foodPreference)}\n"
            f"유통기한 임박 재료: {', '.join(state['expiring_names']) or '없음'}"
        )
        with timed() as t:
            docs = invoke_with_retry(retriever.invoke, query)
        log_event(
            "retrieve",
            state["trace_id"],
            duration_ms=t["duration_ms"],
            query_chars=len(query),
            num_docs=len(docs),
        )
        return {"retrieved_context": _format_docs(docs)}

    def generate_node(state: RecipeAgentState) -> dict:
        profile = state["profile"]
        feedback = state["feedback"]
        feedback_section = (
            f"\n[이전 추천의 문제점 - 반드시 수정하세요]\n{feedback}\n" if feedback else ""
        )
        attempt = state["retry_count"] + 1
        with timed() as t:
            result = invoke_with_retry(
                generate_chain.invoke,
                {
                    "householdType": profile.householdType,
                    "memberCount": profile.memberCount,
                    "cookingEnv": profile.cookingEnv,
                    "foodPreference": profile.foodPreference,
                    "ingredients_text": state["ingredients_text"],
                    "expiring_ingredients_text": state["expiring_ingredients_text"],
                    "retrieved_context": state["retrieved_context"],
                    "feedback_section": feedback_section,
                },
            )

        if result["parsing_error"] is not None:
            raise result["parsing_error"]

        usage = extract_usage(result["raw"], model_name)
        log_event(
            "generate",
            state["trace_id"],
            attempt=attempt,
            duration_ms=t["duration_ms"],
            **usage,
        )
        return {
            "recommendation": result["parsed"],
            "token_usage": state["token_usage"] + [usage],
        }

    def validate_node(state: RecipeAgentState) -> dict:
        with timed() as t:
            issues = validate_recommendation(
                recommendation=state["recommendation"],
                cooking_env=state["profile"].cookingEnv,
                member_count=state["profile"].memberCount,
                fridge_names=[ingredient.name for ingredient in state["ingredients"]],
                expiring_names=state["expiring_names"],
            )
            valid = len(issues) == 0
            retry_count = state["retry_count"] + (0 if valid else 1)
            result = {"valid": valid, "feedback": "\n".join(issues), "retry_count": retry_count}
        log_event(
            "validate",
            state["trace_id"],
            duration_ms=t["duration_ms"],
            valid=result["valid"],
            retry_count=result["retry_count"],
            num_issues=len(issues),
        )
        return result

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
    use_cache: bool = False,
) -> tuple[RecipeRecommendation, RecipeAgentState]:
    """RAG + 검증/재시도 루프를 거쳐 레시피 3개를 추천합니다.

    반환값: (최종 추천 결과, 최종 상태) - 상태에는 검증 결과(valid, feedback,
    retry_count)와 검색된 참고 자료(retrieved_context)가 포함되어 디버깅에 사용할 수 있습니다.
    또한 trace_id로 묶인 구조화 로그(retrieve/generate/validate/request_start/request_end)가
    logs/naengchae.jsonl과 stdout에 기록되고, token_usage에 LLM 호출별 토큰/비용이 쌓입니다.

    use_cache=True면 (profile, ingredients, today)가 완전히 같은 직전 요청이 있을 때
    LLM을 다시 호출하지 않고 그 결과를 재사용합니다(cache.py). 기본값은 False입니다 —
    eval 하니스가 같은 cases.json으로 반복 실행될 때 캐시가 켜져 있으면 두 번째 실행부터
    LLM을 전혀 호출하지 않게 되어 평가 자체가 무의미해지기 때문에, 실제 요청을 받는
    web/main.py 쪽에서만 명시적으로 켭니다.
    """
    today = today or date.today()
    trace_id = str(uuid.uuid4())

    if use_cache:
        cached = cache.get(profile, ingredients, today)
        if cached is not None:
            cached_recommendation, cached_state = cached
            log_event(
                "request_start",
                trace_id,
                household_type=profile.householdType,
                member_count=profile.memberCount,
                cooking_env=profile.cookingEnv,
                food_preference=profile.foodPreference,
                num_ingredients=len(ingredients),
                num_expiring=len(_expiring_names(ingredients, today)),
                cache_hit=True,
            )
            log_event("cache_hit", trace_id, source_trace_id=cached_state["trace_id"])
            new_state = {**cached_state, "trace_id": trace_id}
            log_event(
                "request_end",
                trace_id,
                duration_ms=0.0,
                valid=new_state["valid"],
                retry_count=new_state["retry_count"],
                llm_calls=0,
                total_input_tokens=0,
                total_output_tokens=0,
                total_tokens=0,
                total_cost_usd=0.0,
            )
            return cached_recommendation, new_state

    graph = build_recipe_agent_graph(llm, retriever)

    ingredients_text, expiring_ingredients_text = _format_ingredients(ingredients, today)

    log_event(
        "request_start",
        trace_id,
        household_type=profile.householdType,
        member_count=profile.memberCount,
        cooking_env=profile.cookingEnv,
        food_preference=profile.foodPreference,
        num_ingredients=len(ingredients),
        num_expiring=len(_expiring_names(ingredients, today)),
    )

    initial_state: RecipeAgentState = {
        "trace_id": trace_id,
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
        "token_usage": [],
    }

    with timed() as t:
        final_state = graph.invoke(initial_state, config={"recursion_limit": RECURSION_LIMIT})

    log_event(
        "request_end",
        trace_id,
        duration_ms=t["duration_ms"],
        valid=final_state["valid"],
        retry_count=final_state["retry_count"],
        **summarize_usage(final_state["token_usage"]),
    )

    if use_cache:
        cache.put(profile, ingredients, today, final_state["recommendation"], final_state)

    return final_state["recommendation"], final_state
