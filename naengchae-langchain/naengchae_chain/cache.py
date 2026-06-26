# 추천 결과 캐시 (Phase 5).
#
# 같은 (프로필, 보유 재료, 날짜) 조합으로 다시 추천을 요청하면(예: 사용자가 화면을
# 새로고침하거나 "추천받기"를 두 번 누르는 경우) LLM을 다시 호출하지 않고 직전 결과를
# 재사용합니다. 단일 사용자 앱이고 메모리 캐시라 서버가 재시작되면 비워지지만, 이
# 프로젝트 규모에서는 그 정도로 충분하다고 판단했습니다(영속 캐시(Redis 등)는 과한
# 인프라 추가).
#
# 의도적으로 기본 비활성(opt-in)입니다 — eval 하니스(eval/run_eval.py)가 같은
# cases.json으로 반복 실행될 때 캐시가 켜져 있으면 두 번째 실행부터는 LLM을 전혀
# 호출하지 않고 과거 결과만 반환하게 되어, "평가"라는 목적 자체가 무의미해집니다.
# 그래서 캐시는 web/main.py처럼 실제 사용자 요청을 받는 곳에서만 명시적으로 켭니다.

import hashlib
import json
from datetime import date
from typing import Optional

from .models import FridgeIngredient, RecipeRecommendation, UserProfile

_CACHE: dict[str, tuple[RecipeRecommendation, dict]] = {}
_MAX_ENTRIES = 50  # 단일 사용자 앱이라 넉넉한 값. 넘으면 가장 오래된 항목을 버린다(FIFO).


def _cache_key(profile: UserProfile, ingredients: list[FridgeIngredient], today: date) -> str:
    payload = {
        "profile": profile.model_dump(),
        "ingredients": [i.model_dump() for i in ingredients],
        "today": today.isoformat(),
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get(
    profile: UserProfile, ingredients: list[FridgeIngredient], today: date
) -> Optional[tuple[RecipeRecommendation, dict]]:
    return _CACHE.get(_cache_key(profile, ingredients, today))


def put(
    profile: UserProfile,
    ingredients: list[FridgeIngredient],
    today: date,
    recommendation: RecipeRecommendation,
    state: dict,
) -> None:
    key = _cache_key(profile, ingredients, today)
    if key not in _CACHE and len(_CACHE) >= _MAX_ENTRIES:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = (recommendation, state)


def clear() -> None:
    _CACHE.clear()
