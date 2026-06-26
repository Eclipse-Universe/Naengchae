# 재료 목록 -> 프롬프트 텍스트 변환(chain.py)과 유통기한 임박 판정(graph.py)에 대한
# 단위 테스트입니다. Phase 1에서 "유통기한 임박 재료가 없을 때도 true로 표시되는" 버그가
# 있었던 영역이라, 경계값(D+3, D+0, D-1)을 명시적으로 고정해둡니다.

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from naengchae_chain.chain import EXPIRY_WARNING_DAYS, _format_ingredients
from naengchae_chain.graph import _expiring_names
from naengchae_chain.models import FridgeIngredient

TODAY = date(2026, 6, 26)


def test_format_ingredients_empty_list():
    all_text, expiring_text = _format_ingredients([], TODAY)
    assert "없습니다" in all_text
    assert expiring_text == "(없음)"


def test_format_ingredients_without_expiry_date():
    ingredients = [FridgeIngredient(name="계란", expiryDate=None)]
    all_text, expiring_text = _format_ingredients(ingredients, TODAY)
    assert "계란" in all_text
    assert expiring_text == "(없음)"


def test_format_ingredients_marks_expiring_within_warning_window():
    expiry = (TODAY + timedelta(days=EXPIRY_WARNING_DAYS)).isoformat()
    ingredients = [FridgeIngredient(name="두부", expiryDate=expiry)]
    _, expiring_text = _format_ingredients(ingredients, TODAY)
    assert "두부" in expiring_text


def test_expiring_names_boundary_exactly_at_warning_days():
    # EXPIRY_WARNING_DAYS(3일) 경계: 정확히 3일 남았으면 "임박"으로 잡혀야 한다 (<=)
    expiry = date(2026, 6, 29)  # TODAY + 3
    ingredients = [FridgeIngredient(name="두부", expiryDate=expiry.isoformat())]
    names = _expiring_names(ingredients, TODAY)
    assert names == ["두부"]


def test_expiring_names_just_outside_warning_window():
    expiry = date(2026, 6, 30)  # TODAY + 4, 경계 밖
    ingredients = [FridgeIngredient(name="두부", expiryDate=expiry.isoformat())]
    names = _expiring_names(ingredients, TODAY)
    assert names == []


def test_expiring_names_already_past_expiry_is_still_flagged():
    # 이미 지난 날짜(D-1)도 "임박"(사실은 더 급함)으로 잡혀야 한다.
    expiry = date(2026, 6, 25)  # TODAY - 1
    ingredients = [FridgeIngredient(name="두부", expiryDate=expiry.isoformat())]
    names = _expiring_names(ingredients, TODAY)
    assert names == ["두부"]


def test_expiring_names_empty_when_no_dates_set():
    ingredients = [FridgeIngredient(name="계란", expiryDate=None)]
    assert _expiring_names(ingredients, TODAY) == []
