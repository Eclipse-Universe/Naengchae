# RAG에서 검색 대상이 되는 조리 지식 코퍼스입니다.
# 조리환경별 가능 메뉴, 재료 손질/보관법, 대체 재료, 유통기한 임박 재료 활용법,
# 음식 취향별 특징 등을 짧은 문서로 정리해 FAISS에 인덱싱합니다.

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStoreRetriever

COOKING_KNOWLEDGE: list[Document] = [
    Document(
        page_content="전자레인지(microwave) 조리환경에서는 찜, 데우기, 익히기 위주의 요리만 가능합니다. "
        "계란찜, 단호박찜, 고구마/감자찜, 즉석밥 데우기, 데친야채 조리 등이 적합합니다. "
        "오븐, 에어프라이어, 가스불을 이용한 볶음·구이·팬 요리는 만들 수 없습니다.",
        metadata={"category": "cookingEnv", "env": "microwave"},
    ),
    Document(
        page_content="가스레인지 1구(oneburner) 조리환경에서는 냄비나 프라이팬 하나로 만드는 요리만 가능합니다. "
        "볶음밥, 라면, 찌개, 국, 계란말이, 부침 요리 등이 적합합니다. "
        "전자레인지·오븐·에어프라이어가 필요한 요리는 추천하지 않습니다. "
        "조리 단계에서는 전자레인지 사용을 언급하지 마세요.",
        metadata={"category": "cookingEnv", "env": "oneburner"},
    ),
    Document(
        page_content="풀 조리환경(full)에서는 오븐, 에어프라이어, 인덕션, 가스레인지 등을 모두 활용할 수 있습니다. "
        "구이, 오븐 요리, 에어프라이어 튀김, 다양한 부재료를 활용한 복합 요리까지 추천할 수 있습니다.",
        metadata={"category": "cookingEnv", "env": "full"},
    ),
    Document(
        page_content="두부는 큰 부분과 썬 부분을 나누어 냉장하면 활용도가 높아집니다. "
        "큰 부분은 냄비요리용으로, 썬 부분은 국물 요리나 고명으로 사용합니다. "
        "잘게 썰어 두거나 보관하면 한 달 이상 사용할 수 있어 유통기한 임박 시 냉동을 추천합니다.",
        metadata={"category": "ingredient", "ingredient": "두부"},
    ),
    Document(
        page_content="두부와 같은 콩 식품류는 냉장 보관하면 2~3일 정도 신선하게 유지됩니다. "
        "유통기한이 임박한 두부는 일찌감치 두부조림, 두부김치, 된장찌개 등에 바로 사용하는 것이 좋습니다.",
        metadata={"category": "ingredient", "ingredient": "두부"},
    ),
    Document(
        page_content="계란은 껍질째 냉장 보관하며, 다양한 요리에 활용도가 높은 재료입니다. "
        "계란찜, 계란말이, 스크램블, 볶음밥 토핑 등 어떤 조리환경에서는 쉽게 활용할 수 있습니다.",
        metadata={"category": "ingredient", "ingredient": "계란"},
    ),
    Document(
        page_content="양파와 감자는 상온에서도 오래가고 어두운 곳에서 신문 보관이 가능하지만, 썬 후에는 냉장 보관해야 합니다. "
        "유통기한 임박 양파/감자는 볶음, 국물 요리, 카레 등에 다양하게 활용할 수 있습니다.",
        metadata={"category": "ingredient", "ingredient": "양파/감자"},
    ),
    Document(
        page_content="여러 단위 유통기한 채소들을 한 번에 모아 볶음밥, 잡채죽, 국물 요리에 넣으면 낭비 없이 처리할 수 있습니다. "
        "양이 변하거나 시들기 시작한 야채는 볶음이나 국에 넣어 익혀 먹는 것이 좋습니다.",
        metadata={"category": "ingredient", "ingredient": "유통기한채소"},
    ),
    Document(
        page_content="우유가 없을 때는 두유나 물로 대체할 수 있습니다. "
        "크림 소스나 빵 반죽에는 대신, 단순히 농도를 맞추는 용도라면 물로도 대체 가능합니다.",
        metadata={"category": "substitute", "from": "우유", "to": "두유/물"},
    ),
    Document(
        page_content="버터가 없을 때는 식용유로 대체할 수 있습니다. "
        "식용유로 대체하면 풍미는 다소 떨어지지만 조리에는 큰 문제가 없습니다.",
        metadata={"category": "substitute", "from": "버터", "to": "식용유/마가린"},
    ),
    Document(
        page_content="설탕이 없을 때는 꿀이나 시럽으로 대체할 수 있습니다. "
        "꿀과 시럽은 설탕보다 단맛이 강하므로 양을 약간 줄여서 사용하는 것이 좋습니다.",
        metadata={"category": "substitute", "from": "설탕", "to": "꿀/시럽"},
    ),
    Document(
        page_content="고추장이 없을 때는 된장과 고춧가루, 약간의 설탕을 섞어 비슷한 맛을 낼 수 있습니다. "
        "비율은 된장 2, 고춧가루 1, 설탕 0.5 정도가 적당합니다.",
        metadata={"category": "substitute", "from": "고추장", "to": "된장+고춧가루"},
    ),
    Document(
        page_content="유통기한이 임박한 두부, 계란, 고기류는 같이 조리를 통해 안전하게 섭취하는 것이 좋습니다. "
        "부침, 볶음, 조림 등 충분히 익히는 조리법을 우선 추천합니다.",
        metadata={"category": "expiring", "target": "protein"},
    ),
    Document(
        page_content="유통기한이 임박한 채소는 국물 요리나 볶음에 넣어 익히면 신선도와 무관하게 맛있게 섭취할 수 있습니다. "
        "특히 양이 줄거나 시들었으면 무침으로 활용하기도 좋습니다.",
        metadata={"category": "expiring", "target": "vegetable"},
    ),
    Document(
        page_content="한식(korean)은 밥, 국/찌개, 반찬으로 구성되는 경우가 많으며 간장, 고추장, 된장, 마늘, 두부 등을 "
        "기본 양념으로 활용합니다. 볶음, 조림, 찌개류가 대표적입니다.",
        metadata={"category": "preference", "preference": "korean"},
    ),
    Document(
        page_content="양식(western)은 파스타, 스테이크, 샐러드, 수프 등이 대표적이며 올리브오일, 버터, 치즈, "
        "토마토소스 등을 활용합니다. 오븐이나 프라이팬을 이용한 조리가 많습니다.",
        metadata={"category": "preference", "preference": "western"},
    ),
    Document(
        page_content="일식(japanese)은 된장국(미소시루), 덮밥, 야끼니쿠, 우동 등이 대표적이며 간장, 미린, "
        "가쓰오부시 등을 양념으로 활용합니다. 비교적 간단한 조리법이 많아 1인 가구에 적합합니다.",
        metadata={"category": "preference", "preference": "japanese"},
    ),
    Document(
        page_content="고단백(highprotein) 식단은 닭가슴살, 계란, 두부, 그릭요거트 등 단백질 함량이 높은 재료를 활용한 "
        "요리를 우선 추천합니다. 튀김보다는 구이, 찜, 삶기 등 기름을 적게 쓰는 조리법이 좋습니다.",
        metadata={"category": "preference", "preference": "highprotein"},
    ),
]


def build_vectorstore(embeddings: Embeddings) -> FAISS:
    """조리 지식 코퍼스를 임베딩하여 FAISS 벡터스토어를 만듭니다."""
    return FAISS.from_documents(COOKING_KNOWLEDGE, embeddings)


def build_retriever(embeddings: Embeddings, k: int = 4) -> VectorStoreRetriever:
    """조리 지식 코퍼스에 대한 retriever를 만듭니다."""
    return build_vectorstore(embeddings).as_retriever(search_kwargs={"k": k})
