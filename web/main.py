"""냉채 웹 데모 — FastAPI 백엔드.

기존 naengchae_chain 패키지를 재사용하고
개선 사항을 반영한 API 서버입니다.
"""

import sys
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent / "naengchae-langchain"))

import json

from naengchae_chain import db
from naengchae_chain.graph import build_recipe_agent_graph, recommend_recipes_agent
from naengchae_chain.knowledge_base import build_retriever
from naengchae_chain.models import FridgeIngredient, RecipeRecommendation, UserProfile

# Upstage LLM + 임베딩 (앱 시작 시 1회만 초기화 — 개선점: 캐싱)
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "naengchae-langchain" / ".env")

_retriever = None
_llm = None


def _init_models():
    global _retriever, _llm
    from langchain_upstage import ChatUpstage, UpstageEmbeddings

    embeddings = UpstageEmbeddings(model="solar-embedding-1-large")
    _retriever = build_retriever(embeddings, k=4)
    _llm = ChatUpstage(model="solar-pro3", temperature=0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    _init_models()
    yield


app = FastAPI(title="냉채 웹 데모", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 개선점: tags 코드값 → 한국어 표시명 매핑
TAG_DISPLAY: dict[str, str] = {
    "microwave": "전자레인지",
    "oneburner": "가스레인지 1구",
    "full": "풀옵션",
    "korean": "한식",
    "western": "양식",
    "japanese": "일식",
    "highprotein": "고단백",
    "none": "제한없음",
    "single": "1인가구",
    "family": "가족",
}

PREFERENCE_DISPLAY: dict[str, str] = {
    "korean": "한식",
    "western": "양식",
    "japanese": "일식",
    "highprotein": "고단백",
    "none": "제한없음",
}

COOKING_ENV_DISPLAY: dict[str, str] = {
    "microwave": "전자레인지만",
    "oneburner": "가스레인지 1구",
    "full": "풀옵션",
}


class IngredientIn(BaseModel):
    name: str
    expiryDate: Optional[str] = None


class IngredientOut(BaseModel):
    id: int
    name: str
    expiryDate: Optional[str] = None


class ProfileIn(BaseModel):
    householdType: str
    memberCount: int
    cookingEnv: str
    foodPreference: list[str]


class ProfileOut(ProfileIn):
    pass


class RecommendRequest(BaseModel):
    today: Optional[str] = None


class UsedIngredientOut(BaseModel):
    name: str
    amount: str
    perServingAmount: str


class MissingIngredientOut(BaseModel):
    name: str
    amount: str


class RecipeOut(BaseModel):
    name: str
    cookingTime: int
    servings: int
    usedIngredients: list[UsedIngredientOut]
    missingIngredients: list[MissingIngredientOut]
    tags: list[str]  # 한국어로 변환된 태그
    steps: list[str]
    usesExpiringIngredient: bool


class RecommendResponse(BaseModel):
    recipes: list[RecipeOut]
    valid: bool
    retryCount: int
    feedback: str
    retrievedContext: str


def _convert_tags(tags: list[str]) -> list[str]:
    """코드값 태그를 한국어 표시명으로 변환 (개선점)."""
    return [TAG_DISPLAY.get(t, t) for t in tags]


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/fridge", response_model=list[IngredientOut])
async def list_fridge():
    return [
        IngredientOut(id=row.id, name=row.name, expiryDate=row.expiry_date)
        for row in db.list_ingredients()
    ]


@app.post("/fridge", response_model=IngredientOut)
async def add_fridge_ingredient(ingredient: IngredientIn):
    row = db.add_ingredient(ingredient.name, ingredient.expiryDate)
    return IngredientOut(id=row.id, name=row.name, expiryDate=row.expiry_date)


@app.delete("/fridge/{ingredient_id}")
async def delete_fridge_ingredient(ingredient_id: int):
    deleted = db.delete_ingredient(ingredient_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="해당 재료를 찾을 수 없습니다.")
    return {"deleted": True}


@app.get("/profile", response_model=Optional[ProfileOut])
async def get_profile():
    row = db.get_profile()
    if row is None:
        return None
    return ProfileOut(
        householdType=row.household_type,
        memberCount=row.member_count,
        cookingEnv=row.cooking_env,
        foodPreference=json.loads(row.food_preference),
    )


@app.post("/profile", response_model=ProfileOut)
async def save_profile(profile: ProfileIn):
    row = db.save_profile(
        profile.householdType, profile.memberCount, profile.cookingEnv, profile.foodPreference
    )
    return ProfileOut(
        householdType=row.household_type,
        memberCount=row.member_count,
        cookingEnv=row.cooking_env,
        foodPreference=json.loads(row.food_preference),
    )


@app.post("/recommend", response_model=RecommendResponse)
async def recommend(req: RecommendRequest):
    if _llm is None or _retriever is None:
        raise HTTPException(status_code=503, detail="모델 초기화 중입니다. 잠시 후 다시 시도하세요.")

    profile_row = db.get_profile()
    if profile_row is None:
        raise HTTPException(status_code=400, detail="프로필이 없습니다. 먼저 프로필을 설정하세요.")

    try:
        profile = UserProfile(
            householdType=profile_row.household_type,
            memberCount=profile_row.member_count,
            cookingEnv=profile_row.cooking_env,
            foodPreference=json.loads(profile_row.food_preference),
        )
        ingredients = [
            FridgeIngredient(name=row.name, expiryDate=row.expiry_date)
            for row in db.list_ingredients()
        ]
        today = date.fromisoformat(req.today) if req.today else date.today()

        recommendation, final_state = recommend_recipes_agent(
            _llm, _retriever, profile, ingredients, today
        )

        recipes_out = [
            RecipeOut(
                name=r.name,
                cookingTime=r.cookingTime,
                servings=r.servings,
                usedIngredients=[
                    UsedIngredientOut(name=u.name, amount=u.amount, perServingAmount=u.perServingAmount)
                    for u in r.usedIngredients
                ],
                missingIngredients=[
                    MissingIngredientOut(name=m.name, amount=m.amount)
                    for m in r.missingIngredients
                ],
                tags=_convert_tags(r.tags),  # 개선점: 코드값 → 한국어
                steps=r.steps,
                usesExpiringIngredient=r.usesExpiringIngredient,
            )
            for r in recommendation.recipes
        ]

        return RecommendResponse(
            recipes=recipes_out,
            valid=final_state["valid"],
            retryCount=final_state["retry_count"],
            feedback=final_state["feedback"],
            retrievedContext=final_state["retrieved_context"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
