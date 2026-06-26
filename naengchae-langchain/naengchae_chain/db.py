"""SQLite 영속 계층 (Phase 4).

단일 사용자를 가정한다(로그인/인증이 없으므로 — 자세한 이유는
docs/ENGINEERING_LOG.md Phase 4 항목 참고). 냉장고 재료는 여러 행, 사용자 프로필은
항상 id=1인 단일 행으로 관리한다.

SQLModel을 선택한 이유: 이 프로젝트는 이미 Pydantic으로 모든 데이터 모델
(UserProfile, FridgeIngredient 등)을 정의하고 있다. SQLModel은 Pydantic
BaseModel을 그대로 ORM 테이블로 쓸 수 있게 해주므로, 새 패러다임을 추가하지
않고 기존 스키마 정의 방식을 DB까지 그대로 연장할 수 있다.
"""

import json
import os
from pathlib import Path
from typing import Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("NAENGCHAE_DB_PATH", PACKAGE_ROOT / "naengchae.db"))

_engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


class FridgeIngredientRow(SQLModel, table=True):
    __tablename__ = "fridge_ingredients"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    expiry_date: Optional[str] = None


class UserProfileRow(SQLModel, table=True):
    __tablename__ = "user_profile"

    id: int = Field(default=1, primary_key=True)  # 단일 사용자 — 항상 1행만 존재
    household_type: str
    member_count: int
    cooking_env: str
    food_preference: str  # JSON 인코딩된 list[str]


def init_db() -> None:
    SQLModel.metadata.create_all(_engine)


def list_ingredients() -> list[FridgeIngredientRow]:
    with Session(_engine) as session:
        return list(session.exec(select(FridgeIngredientRow)))


def add_ingredient(name: str, expiry_date: Optional[str]) -> FridgeIngredientRow:
    with Session(_engine) as session:
        row = FridgeIngredientRow(name=name, expiry_date=expiry_date)
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def delete_ingredient(ingredient_id: int) -> bool:
    with Session(_engine) as session:
        row = session.get(FridgeIngredientRow, ingredient_id)
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True


def get_profile() -> Optional[UserProfileRow]:
    with Session(_engine) as session:
        return session.get(UserProfileRow, 1)


def save_profile(
    household_type: str, member_count: int, cooking_env: str, food_preference: list[str]
) -> UserProfileRow:
    with Session(_engine) as session:
        row = session.get(UserProfileRow, 1)
        if row is None:
            row = UserProfileRow(id=1, household_type=household_type, member_count=member_count,
                                  cooking_env=cooking_env, food_preference=json.dumps(food_preference))
        else:
            row.household_type = household_type
            row.member_count = member_count
            row.cooking_env = cooking_env
            row.food_preference = json.dumps(food_preference)
        session.add(row)
        session.commit()
        session.refresh(row)
        return row
