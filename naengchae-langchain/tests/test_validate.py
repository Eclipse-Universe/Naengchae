# validate_recommendation()에 대한 단위 테스트입니다.
# 이 함수는 이 프로젝트의 핵심(LLM 출력을 코드로 재검증하는 결정론적 규칙)이라,
# Phase 1에서 발견한 버그들(전자레인지+찜 모순, 유통기한 오탐 등)이 회귀하지 않도록
# 각 규칙을 독립적으로 고정해두는 게 목적입니다. LLM/그래프를 띄우지 않고 순수 함수만
# 테스트하므로 비용 없이 빠르게 돕니다.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from naengchae_chain.graph import validate_recommendation
from naengchae_chain.models import Recipe, RecipeRecommendation, UsedIngredient


def make_recipe(**overrides) -> Recipe:
    defaults = dict(
        name="계란찜",
        cookingTime=10,
        servings=2,
        usedIngredients=[UsedIngredient(name="계란", amount="4개", perServingAmount="2개")],
        missingIngredients=[],
        tags=[],
        steps=["계란을 풀어 그릇에 담는다.", "전자레인지에 3분 돌린다."],
        usesExpiringIngredient=False,
    )
    defaults.update(overrides)
    return Recipe(**defaults)


def make_recommendation(*recipes: Recipe) -> RecipeRecommendation:
    return RecipeRecommendation(recipes=list(recipes))


def test_valid_recipe_has_no_issues():
    rec = make_recommendation(make_recipe(servings=2))
    issues = validate_recommendation(
        recommendation=rec,
        cooking_env="microwave",
        member_count=2,
        fridge_names=["계란"],
        expiring_names=[],
    )
    assert issues == []


def test_forbidden_cooking_method_is_caught():
    # microwave 환경인데 "팬"을 쓰는 조리 단계가 있으면 잡혀야 한다.
    rec = make_recommendation(
        make_recipe(steps=["팬에 기름을 두르고 굽는다."])
    )
    issues = validate_recommendation(
        recommendation=rec,
        cooking_env="microwave",
        member_count=2,
        fridge_names=["계란"],
        expiring_names=[],
    )
    assert any("환경에서는" in issue for issue in issues)


def test_microwave_steam_dish_is_allowed():
    # Phase 1에서 고친 회귀 버그: 전자레인지 환경에서 "찜" 요리(계란찜) 자체는
    # 금지 키워드 목록에 없으므로 막히면 안 된다.
    rec = make_recommendation(make_recipe(name="계란찜", steps=["전자레인지에 3분 돌린다."]))
    issues = validate_recommendation(
        recommendation=rec,
        cooking_env="microwave",
        member_count=2,
        fridge_names=["계란"],
        expiring_names=[],
    )
    assert issues == []


def test_used_ingredient_not_in_fridge_is_caught():
    rec = make_recommendation(
        make_recipe(usedIngredients=[UsedIngredient(name="두부", amount="1모", perServingAmount="0.5모")])
    )
    issues = validate_recommendation(
        recommendation=rec,
        cooking_env="full",
        member_count=2,
        fridge_names=["계란"],  # 두부는 보유 목록에 없음
        expiring_names=[],
    )
    assert any("보유 재료 목록에 없습니다" in issue for issue in issues)


def test_basic_seasoning_is_not_required_in_fridge():
    rec = make_recommendation(
        make_recipe(usedIngredients=[UsedIngredient(name="소금", amount="1꼬집", perServingAmount="0.5꼬집")])
    )
    issues = validate_recommendation(
        recommendation=rec,
        cooking_env="full",
        member_count=2,
        fridge_names=[],  # 소금은 기본 조미료라 보유 목록에 없어도 통과해야 함
        expiring_names=[],
    )
    assert issues == []


def test_expiring_flag_false_positive_is_caught():
    # usesExpiringIngredient=True인데 실제로는 임박 재료를 안 쓴 경우.
    rec = make_recommendation(
        make_recipe(
            usedIngredients=[UsedIngredient(name="계란", amount="2개", perServingAmount="1개")],
            usesExpiringIngredient=True,
        )
    )
    issues = validate_recommendation(
        recommendation=rec,
        cooking_env="full",
        member_count=2,
        fridge_names=["계란", "두부"],
        expiring_names=["두부"],  # 임박 재료는 두부인데 레시피는 계란만 씀
    )
    assert any("실제로 사용하지 않았습니다" in issue for issue in issues)


def test_no_expiring_ingredients_means_no_recipe_needs_to_use_one():
    rec = make_recommendation(make_recipe(usesExpiringIngredient=False))
    issues = validate_recommendation(
        recommendation=rec,
        cooking_env="full",
        member_count=2,
        fridge_names=["계란"],
        expiring_names=[],  # 임박 재료 없음
    )
    assert issues == []


def test_expiring_ingredient_unused_by_any_recipe_is_caught():
    rec = make_recommendation(make_recipe(usesExpiringIngredient=False))
    issues = validate_recommendation(
        recommendation=rec,
        cooking_env="full",
        member_count=2,
        fridge_names=["계란", "두부"],
        expiring_names=["두부"],  # 임박 재료가 있는데 아무 레시피도 안 씀
    )
    assert any("하나도 없습니다" in issue for issue in issues)


def test_servings_mismatch_is_caught():
    rec = make_recommendation(make_recipe(servings=2))
    issues = validate_recommendation(
        recommendation=rec,
        cooking_env="full",
        member_count=4,  # 가구원 4명인데 레시피는 2인분
        fridge_names=["계란"],
        expiring_names=[],
    )
    assert any("servings가 2인분인데" in issue for issue in issues)


def test_oneburner_forbids_microwave_keyword():
    rec = make_recommendation(make_recipe(steps=["전자레인지에 데운다."]))
    issues = validate_recommendation(
        recommendation=rec,
        cooking_env="oneburner",
        member_count=2,
        fridge_names=["계란"],
        expiring_names=[],
    )
    assert any("환경에서는" in issue for issue in issues)


def test_full_env_has_no_forbidden_keywords():
    rec = make_recommendation(make_recipe(steps=["오븐에 20분 굽는다."]))
    issues = validate_recommendation(
        recommendation=rec,
        cooking_env="full",
        member_count=2,
        fridge_names=["계란"],
        expiring_names=[],
    )
    assert issues == []
