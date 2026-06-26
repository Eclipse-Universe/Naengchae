# db.py(SQLite 영속 계층)에 대한 단위 테스트입니다.
# Phase 4-1에서 Python urllib로 한 번 수동 스모크 테스트만 했었는데, 그 이후로 회귀를
# 막아주는 자동 테스트가 없었습니다 - 이번에 추가합니다.
#
# 주의: db.py는 모듈 임포트 시점에 NAENGCHAE_DB_PATH를 읽어 SQLAlchemy 엔진을 만들기
# 때문에, 운영 DB(naengchae.db)를 건드리지 않으려면 db.py를 임포트하기 *전에* 이 환경
# 변수를 임시 파일로 가리키게 바꿔둬야 합니다.

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_tmp_db_fd, _tmp_db_path = tempfile.mkstemp(suffix=".db")
os.close(_tmp_db_fd)
os.environ["NAENGCHAE_DB_PATH"] = _tmp_db_path

from naengchae_chain import db  # noqa: E402  (환경변수 설정 후에 임포트해야 함)

db.init_db()


def setup_function():
    # 테스트마다 깨끗한 상태로 시작하도록 모든 재료를 지운다.
    for row in db.list_ingredients():
        db.delete_ingredient(row.id)


def test_add_and_list_ingredient():
    db.add_ingredient("계란", None)
    rows = db.list_ingredients()
    assert len(rows) == 1
    assert rows[0].name == "계란"
    assert rows[0].expiry_date is None


def test_add_ingredient_with_expiry_date():
    row = db.add_ingredient("두부", "2026-07-01")
    assert row.expiry_date == "2026-07-01"


def test_delete_ingredient_returns_true_when_found():
    row = db.add_ingredient("양파", None)
    assert db.delete_ingredient(row.id) is True
    assert db.list_ingredients() == []


def test_delete_ingredient_returns_false_when_not_found():
    assert db.delete_ingredient(999999) is False


def test_save_and_get_profile_upserts():
    db.save_profile("single", 1, "microwave", ["korean"])
    profile = db.get_profile()
    assert profile.household_type == "single"
    assert profile.member_count == 1

    # 같은 id(=1)로 다시 저장하면 새 행이 아니라 기존 행이 갱신돼야 한다(upsert).
    db.save_profile("family", 3, "full", ["korean", "highprotein"])
    profile = db.get_profile()
    assert profile.household_type == "family"
    assert profile.member_count == 3
    assert profile.id == 1
