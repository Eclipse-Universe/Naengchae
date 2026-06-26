# cache.py에 대한 단위 테스트입니다. LLM 호출 없이 캐시 키 계산과 hit/miss만 검증합니다.

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from naengchae_chain import cache
from naengchae_chain.models import FridgeIngredient, Recipe, RecipeRecommendation, UsedIngredient, UserProfile


def setup_function():
    cache.clear()


def make_profile(member_count=2):
    return UserProfile(
        householdType="single" if member_count == 1 else "family",
        memberCount=member_count,
        cookingEnv="full",
        foodPreference=["korean"],
    )


def make_recommendation():
    return RecipeRecommendation(
        recipes=[
            Recipe(
                name="계란찜",
                cookingTime=10,
                servings=2,
                usedIngredients=[UsedIngredient(name="계란", amount="2개", perServingAmount="1개")],
                missingIngredients=[],
                tags=[],
                steps=["전자레인지에 돌린다."],
                usesExpiringIngredient=False,
            )
        ]
    )


def test_miss_when_nothing_cached():
    profile = make_profile()
    ingredients = [FridgeIngredient(name="계란", expiryDate=None)]
    assert cache.get(profile, ingredients, date(2026, 6, 26)) is None


def test_hit_after_put_with_identical_inputs():
    profile = make_profile()
    ingredients = [FridgeIngredient(name="계란", expiryDate=None)]
    today = date(2026, 6, 26)
    rec = make_recommendation()
    state = {"trace_id": "abc", "valid": True, "retry_count": 0}

    cache.put(profile, ingredients, today, rec, state)
    cached = cache.get(profile, ingredients, today)

    assert cached is not None
    cached_rec, cached_state = cached
    assert cached_rec.recipes[0].name == "계란찜"
    assert cached_state["trace_id"] == "abc"


def test_miss_when_ingredients_differ():
    profile = make_profile()
    today = date(2026, 6, 26)
    rec = make_recommendation()
    cache.put(profile, [FridgeIngredient(name="계란", expiryDate=None)], today, rec, {})

    miss = cache.get(profile, [FridgeIngredient(name="두부", expiryDate=None)], today)
    assert miss is None


def test_miss_when_date_differs():
    profile = make_profile()
    ingredients = [FridgeIngredient(name="계란", expiryDate=None)]
    rec = make_recommendation()
    cache.put(profile, ingredients, date(2026, 6, 26), rec, {})

    miss = cache.get(profile, ingredients, date(2026, 6, 27))
    assert miss is None


def test_miss_when_member_count_differs():
    ingredients = [FridgeIngredient(name="계란", expiryDate=None)]
    today = date(2026, 6, 26)
    rec = make_recommendation()
    cache.put(make_profile(member_count=2), ingredients, today, rec, {})

    miss = cache.get(make_profile(member_count=4), ingredients, today)
    assert miss is None
