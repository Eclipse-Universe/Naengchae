"""영속 계층 (Phase 4 SQLite, Phase 6 배포용 PostgreSQL 지원 추가).

단일 사용자를 가정한다(로그인/인증이 없으므로 — 자세한 이유는
docs/ENGINEERING_LOG.md Phase 4 항목 참고). 냉장고 재료는 여러 행, 사용자 프로필은
항상 id=1인 단일 행으로 관리한다.

SQLModel을 선택한 이유: 이 프로젝트는 이미 Pydantic으로 모든 데이터 모델
(UserProfile, FridgeIngredient 등)을 정의하고 있다. SQLModel은 Pydantic
BaseModel을 그대로 ORM 테이블로 쓸 수 있게 해주므로, 새 패러다임을 추가하지
않고 기존 스키마 정의 방식을 DB까지 그대로 연장할 수 있다.

DATABASE_URL 환경변수가 있으면 그걸 그대로 쓴다(Render의 무료 PostgreSQL이 자동으로
이 변수를 주입한다). 없으면 로컬 개발용 SQLite 파일로 그대로 동작한다 — Render의 무료
웹 서비스는 파일시스템이 재시작마다 초기화되는 휘발성이라(영구 디스크는 유료 플랜에만
있음) SQLite로 배포하면 재시작될 때마다 데이터가 사라지기 때문에, 배포 시에는 반드시
DATABASE_URL(Postgres)을 설정해야 한다. 로컬 개발에서는 SQLite 파일 하나로 충분해서
굳이 Postgres를 띄울 필요가 없으므로, 이 분기로 두 환경 다 자연스럽게 지원한다.
"""

import json
import os
from pathlib import Path
from typing import Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("NAENGCHAE_DB_PATH", PACKAGE_ROOT / "naengchae.db"))

_database_url = os.environ.get("DATABASE_URL")
if _database_url:
    # SQLAlchemy 1.4+는 "postgres://"를 더 이상 인식하지 않고 "postgresql://"만 받는다.
    # Render/Heroku류 플랫폼이 옛 스킴으로 주입하는 경우가 있어 방어적으로 변환한다.
    if _database_url.startswith("postgres://"):
        _database_url = _database_url.replace("postgres://", "postgresql://", 1)
    # 재료/태그에 한글이 들어가므로 서버의 기본 인코딩에 의존하지 않고 명시한다
    # (테스트 중 SQL_ASCII로 초기화된 Postgres 클러스터에서 한글 INSERT가 깨지는 걸
    # 직접 확인했음 — Render의 관리형 Postgres는 기본이 UTF8이라 거기선 문제 없지만,
    # 다른 호스팅으로 옮길 가능성에도 안전하게 대응해둔다).
    _engine = create_engine(_database_url, connect_args={"client_encoding": "utf8"})
else:
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
