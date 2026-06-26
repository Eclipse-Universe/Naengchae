# RAG에서 검색 대상이 되는 조리 지식 코퍼스입니다.
# 조리환경별 가능 메뉴, 재료 손질/보관/대체법, 유통기한 임박 재료 활용법,
# 음식 취향별 특징, 조리환경×취향 조합, 가구 규모별 팁을 짧은 문서로 정리해 FAISS에 인덱싱합니다.
#
# Phase 3에서 17개 -> 약 100개로 확장했습니다. 확장 전략과 이유는
# docs/ENGINEERING_LOG.md, naengchae-langchain/eval/RETRIEVAL_EVAL.md 참고.
# 각 Document의 metadata["id"]는 retrieval 평가(eval/retrieval_cases.json)에서
# ground truth로 참조하는 안정적인 식별자입니다 — page_content를 고쳐도 id는 바꾸지 마세요.

import os
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStoreRetriever

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
# Phase 6(배포)에서 추가: 코퍼스(94개 문서)를 매번 임베딩하면 콜드스타트(예: Render 무료
# 티어의 15분 슬립 후 재시작)마다 Upstage 임베딩 API를 94번씩 호출하게 된다. 인덱스를
# 디스크에 저장해두고 재사용하면 그 비용/지연을 없앨 수 있다. 이 디렉터리는 git에
# 커밋해서 배포 환경의 "파일시스템이 휘발성이어도 git checkout으로는 항상 존재하는"
# 특성을 이용한다 — 런타임에 새로 쓰는 데이터(SQLite 등)와는 달리 이 인덱스는 코드와
# 같이 배포되는 정적 자산으로 취급한다.
FAISS_INDEX_DIR = Path(
    os.environ.get("NAENGCHAE_FAISS_INDEX_DIR", PACKAGE_ROOT / "faiss_index")
)

COOKING_KNOWLEDGE: list[Document] = [
    # ── 조리환경 (env) ──────────────────────────────────────────────
    Document(
        page_content="전자레인지(microwave) 조리환경에서는 찜, 데우기, 익히기 위주의 요리만 가능합니다. "
        "계란찜, 단호박찜, 고구마/감자찜, 즉석밥 데우기, 데친야채 조리 등이 적합합니다. "
        "오븐, 에어프라이어, 가스불을 이용한 볶음·구이·팬 요리는 만들 수 없습니다.",
        metadata={"id": "env-001", "category": "cookingEnv", "env": "microwave"},
    ),
    Document(
        page_content="전자레인지로 만들 수 있는 구체적인 메뉴: 계란찜, 두부계란찜, 단호박찜, 감자/고구마찜, "
        "즉석밥+냉장 반찬 데우기, 냉동 만두 데우기, 컵라면. 내열용기에 재료와 물을 넣고 랩이나 뚜껑을 "
        "덮어 익히는 방식이 핵심이며, 기름에 굽거나 볶는 조리는 불가능합니다.",
        metadata={"id": "env-002", "category": "cookingEnv", "env": "microwave"},
    ),
    Document(
        page_content="가스레인지 1구(oneburner) 조리환경에서는 냄비나 프라이팬 하나로 만드는 요리만 가능합니다. "
        "볶음밥, 라면, 찌개, 국, 계란말이, 부침 요리 등이 적합합니다. "
        "전자레인지·오븐·에어프라이어가 필요한 요리는 추천하지 않습니다. "
        "조리 단계에서는 전자레인지 사용을 언급하지 마세요.",
        metadata={"id": "env-003", "category": "cookingEnv", "env": "oneburner"},
    ),
    Document(
        page_content="가스레인지 1구로 만들 수 있는 구체적인 메뉴: 김치찌개, 된장찌개, 계란말이, 볶음밥, "
        "각종 전(부침개), 라면, 카레, 미역국. 냄비 하나 또는 프라이팬 하나로 처음부터 끝까지 조리가 "
        "끝나는 한 그릇 요리 위주로 추천하는 것이 좋습니다.",
        metadata={"id": "env-004", "category": "cookingEnv", "env": "oneburner"},
    ),
    Document(
        page_content="풀 조리환경(full)에서는 오븐, 에어프라이어, 인덕션, 가스레인지 등을 모두 활용할 수 있습니다. "
        "구이, 오븐 요리, 에어프라이어 튀김, 다양한 부재료를 활용한 복합 요리까지 추천할 수 있습니다.",
        metadata={"id": "env-005", "category": "cookingEnv", "env": "full"},
    ),
    Document(
        page_content="풀 조리환경에서 추가로 가능한 구체적 메뉴: 에어프라이어 치킨/감자튀김, 오븐 그라탕, "
        "오븐 구이 채소, 스테이크, 파스타 베이크. 여러 조리기구를 동시에 쓰는 코스 요리나 시간이 걸리는 "
        "오븐 요리도 자유롭게 추천할 수 있습니다.",
        metadata={"id": "env-006", "category": "cookingEnv", "env": "full"},
    ),
    # ── 재료 보관/손질 (ingredient) ────────────────────────────────
    Document(
        page_content="두부는 큰 부분과 썬 부분을 나누어 냉장하면 활용도가 높아집니다. "
        "큰 부분은 냄비요리용으로, 썬 부분은 국물 요리나 고명으로 사용합니다. "
        "잘게 썰어 두거나 보관하면 한 달 이상 사용할 수 있어 유통기한 임박 시 냉동을 추천합니다.",
        metadata={"id": "ingredient-001", "category": "ingredient", "ingredient": "두부"},
    ),
    Document(
        page_content="두부와 같은 콩 식품류는 냉장 보관하면 2~3일 정도 신선하게 유지됩니다. "
        "유통기한이 임박한 두부는 일찌감치 두부조림, 두부김치, 된장찌개 등에 바로 사용하는 것이 좋습니다.",
        metadata={"id": "ingredient-002", "category": "ingredient", "ingredient": "두부"},
    ),
    Document(
        page_content="계란은 껍질째 냉장 보관하며, 다양한 요리에 활용도가 높은 재료입니다. "
        "계란찜, 계란말이, 스크램블, 볶음밥 토핑 등 어떤 조리환경에서든 쉽게 활용할 수 있습니다.",
        metadata={"id": "ingredient-003", "category": "ingredient", "ingredient": "계란"},
    ),
    Document(
        page_content="계란은 보통 1인당 1~2개를 기준으로 사용하며, 여러 개를 한꺼번에 풀어 찜이나 국물 요리에 "
        "넣으면 부드러운 식감을 낼 수 있습니다. 신선도가 의심되면 물에 띄워 가라앉는지로 확인합니다.",
        metadata={"id": "ingredient-004", "category": "ingredient", "ingredient": "계란"},
    ),
    Document(
        page_content="양파는 상온에서도 오래가고 어두운 곳에서 신문지에 싸서 보관이 가능하지만, 썬 후에는 "
        "냉장 보관해야 합니다. 유통기한 임박 양파는 볶음, 국물 요리, 카레 등에 다양하게 활용할 수 있습니다.",
        metadata={"id": "ingredient-005", "category": "ingredient", "ingredient": "양파"},
    ),
    Document(
        page_content="양파는 거의 모든 한식·양식 요리의 기본 베이스로 쓰이며, 볶으면 단맛이 강해져 카레나 "
        "스튜의 풍미를 끌어올립니다. 매운맛이 강한 양파는 찬물에 담가두면 매운맛이 줄어듭니다.",
        metadata={"id": "ingredient-006", "category": "ingredient", "ingredient": "양파"},
    ),
    Document(
        page_content="감자는 상온의 어둡고 서늘한 곳에서 오래 보관할 수 있지만, 싹이 나면 그 부분을 깊게 "
        "도려내고 사용해야 합니다. 유통기한 임박 감자는 찜, 조림, 국물 요리에 우선 사용하는 것이 좋습니다.",
        metadata={"id": "ingredient-007", "category": "ingredient", "ingredient": "감자"},
    ),
    Document(
        page_content="감자는 전자레인지로도 쉽게 찔 수 있어(랩에 싸서 5~7분) 모든 조리환경에서 활용도가 "
        "높습니다. 으깬 감자는 샐러드나 그라탕 재료로, 채 썬 감자는 볶음이나 전에 적합합니다.",
        metadata={"id": "ingredient-008", "category": "ingredient", "ingredient": "감자"},
    ),
    Document(
        page_content="당근은 냉장 보관하면 2~3주까지 신선도가 유지되며, 썰어둔 당근은 밀폐용기에 보관해야 "
        "수분이 마르지 않습니다. 유통기한 임박 당근은 볶음, 국물, 카레, 잡채에 두루 활용할 수 있습니다.",
        metadata={"id": "ingredient-009", "category": "ingredient", "ingredient": "당근"},
    ),
    Document(
        page_content="당근은 익히면 단맛이 올라오고 색이 선명해져 볶음 요리의 색감을 살리는 데 자주 "
        "쓰입니다. 채썰어 볶음밥이나 잡채에 넣거나, 큼직하게 썰어 조림·찜에 넣어도 잘 어울립니다.",
        metadata={"id": "ingredient-010", "category": "ingredient", "ingredient": "당근"},
    ),
    Document(
        page_content="대파는 흰 부분과 푸른 부분을 나눠 보관하면 좋습니다. 흰 부분은 양념·볶음 베이스로, "
        "푸른 부분은 국물 요리의 고명이나 향을 내는 용도로 씁니다. 냉동 보관도 잘 됩니다.",
        metadata={"id": "ingredient-011", "category": "ingredient", "ingredient": "대파"},
    ),
    Document(
        page_content="대파는 거의 모든 한식 국물·볶음 요리에 향신 재료로 들어가며, 잘게 썰어 마지막에 "
        "넣으면 향이 살고 오래 끓이면 단맛이 우러납니다. 유통기한 임박 시 잘게 썰어 냉동해두면 오래 씁니다.",
        metadata={"id": "ingredient-012", "category": "ingredient", "ingredient": "대파"},
    ),
    Document(
        page_content="마늘(다진 마늘 포함)은 거의 모든 한식 양념의 기본 재료로, 소금/간장과 함께 기본 "
        "조미료로 간주합니다. 다진 마늘은 냉동 보관하면 소량씩 덜어 쓰기 편하고 오래 보관할 수 있습니다.",
        metadata={"id": "ingredient-013", "category": "ingredient", "ingredient": "마늘"},
    ),
    Document(
        page_content="단호박은 통째로는 상온에서 비교적 오래 보관되지만, 자른 후에는 냉장 보관하고 빨리 "
        "사용해야 합니다. 전자레인지로 쉽게 찔 수 있어(껍질째 5~8분) 모든 조리환경에서 활용 가능합니다.",
        metadata={"id": "ingredient-014", "category": "ingredient", "ingredient": "단호박"},
    ),
    Document(
        page_content="닭가슴살은 냉장 보관 시 1~2일 내에 조리해야 하며, 오래 두려면 냉동이 안전합니다. "
        "삶기, 찌기, 굽기 등 기름을 적게 쓰는 조리법이 잘 어울리고 고단백 식단에 자주 쓰입니다.",
        metadata={"id": "ingredient-015", "category": "ingredient", "ingredient": "닭가슴살"},
    ),
    Document(
        page_content="닭가슴살은 전자레인지로도 찜처럼 익힐 수 있어(내열용기+물 소량, 랩 덮어 5~6분) "
        "전자레인지 환경에서도 고단백 메뉴를 만들 수 있는 핵심 재료입니다. 너무 오래 익히면 질겨집니다.",
        metadata={"id": "ingredient-016", "category": "ingredient", "ingredient": "닭가슴살"},
    ),
    Document(
        page_content="닭다리살은 지방이 있어 구이·조림에 적합하며, 가스레인지 1구나 풀옵션 환경에서 "
        "조림·볶음·구이로 다양하게 활용할 수 있습니다. 냉장 보관 시 2일 이내 조리를 권장합니다.",
        metadata={"id": "ingredient-017", "category": "ingredient", "ingredient": "닭다리살"},
    ),
    Document(
        page_content="돼지고기(목살·앞다리 등)는 냉장 2~3일, 냉동은 1개월 이상 보관 가능합니다. "
        "볶음, 조림, 찌개(김치찌개, 된장찌개)에 두루 쓰이며 충분히 익혀 먹는 것이 중요합니다.",
        metadata={"id": "ingredient-018", "category": "ingredient", "ingredient": "돼지고기"},
    ),
    Document(
        page_content="삼겹살은 지방이 많아 구이에 가장 잘 어울리지만, 가스레인지 1구에서는 두툼한 통삼겹 "
        "구이보다 잘게 썰어 볶음이나 김치찌개에 넣는 것이 더 적합합니다. 냉장 2일 이내 조리를 권장합니다.",
        metadata={"id": "ingredient-019", "category": "ingredient", "ingredient": "삼겹살"},
    ),
    Document(
        page_content="소고기는 부위에 따라 조리법이 크게 달라지지만, 가정에서는 불고기용/국거리용으로 "
        "썰린 형태가 많아 볶음이나 국물 요리에 적합합니다. 냉장 2일, 냉동 1개월 이상 보관 가능합니다.",
        metadata={"id": "ingredient-020", "category": "ingredient", "ingredient": "소고기"},
    ),
    Document(
        page_content="배추는 겉잎으로 한번 감싸 냉장 보관하면 수분이 덜 빠집니다. 김치찌개, 배추된장국, "
        "배추전, 데쳐서 쌈으로 활용할 수 있고 유통기한 임박 시 국물 요리에 넣어 익히는 것이 좋습니다.",
        metadata={"id": "ingredient-021", "category": "ingredient", "ingredient": "배추"},
    ),
    Document(
        page_content="애호박은 무르기 쉬워 냉장 보관하고 빨리 사용하는 것이 좋습니다. 된장찌개, 애호박전, "
        "볶음에 자주 쓰이며 가스레인지 1구 환경에서도 손쉽게 조리할 수 있는 채소입니다.",
        metadata={"id": "ingredient-022", "category": "ingredient", "ingredient": "애호박"},
    ),
    Document(
        page_content="버섯(표고/양송이/느타리 등)은 물에 씻으면 빨리 무르므로 마른 천으로 닦아 보관하는 "
        "것이 좋습니다. 볶음, 국물, 전 어디에나 잘 어울리고 향이 강해 적은 양으로도 풍미를 더합니다.",
        metadata={"id": "ingredient-023", "category": "ingredient", "ingredient": "버섯"},
    ),
    Document(
        page_content="버터가 없을 때는 식용유로 대체할 수 있습니다. "
        "식용유로 대체하면 풍미는 다소 떨어지지만 조리에는 큰 문제가 없습니다.",
        metadata={"id": "ingredient-024", "category": "ingredient", "ingredient": "버터"},
    ),
    Document(
        page_content="치즈는 종류에 따라 가열 시 녹는 정도가 다릅니다. 모짜렐라·체다는 잘 녹아 그라탕·"
        "토스트에 적합하고, 냉장 보관 시 밀폐해서 마르지 않게 해야 합니다.",
        metadata={"id": "ingredient-025", "category": "ingredient", "ingredient": "치즈"},
    ),
    Document(
        page_content="그릭요거트는 일반 요거트보다 단백질이 높아 고단백 식단에 자주 활용됩니다. 그대로 "
        "먹거나 샐러드 드레싱, 닭가슴살 마리네이드에 활용하면 좋습니다. 냉장 보관 필수입니다.",
        metadata={"id": "ingredient-026", "category": "ingredient", "ingredient": "그릭요거트"},
    ),
    Document(
        page_content="아스파라거스는 줄기 끝을 살짝 잘라 물에 담가 보관하면 더 오래 신선합니다. 구이, "
        "볶음, 데치기 모두 잘 어울리는 양식 채소로 오븐이나 팬에서 살짝만 익히는 것이 좋습니다.",
        metadata={"id": "ingredient-027", "category": "ingredient", "ingredient": "아스파라거스"},
    ),
    Document(
        page_content="리코타치즈는 부드럽고 수분이 많아 파스타 소스, 샐러드, 오븐 베이크 요리에 잘 "
        "어울립니다. 개봉 후에는 냉장 보관하고 며칠 내로 사용하는 것이 좋습니다.",
        metadata={"id": "ingredient-028", "category": "ingredient", "ingredient": "리코타치즈"},
    ),
    Document(
        page_content="우동면은 생면/냉동면 형태가 많고, 끓는 물에 데치기만 하면 되어 가스레인지 1구 "
        "환경에서도 빠르게 조리할 수 있습니다. 국물우동, 볶음우동 모두 무난하게 잘 어울립니다.",
        metadata={"id": "ingredient-029", "category": "ingredient", "ingredient": "우동면"},
    ),
    Document(
        page_content="파스타면은 끓는 물에 삶아야 해서 가스레인지 1구로도 가능하지만, 소스를 볶거나 "
        "오븐에 베이크하는 과정까지 더하려면 풀옵션 환경이 더 유리합니다. 삶은 면은 빨리 사용해야 합니다.",
        metadata={"id": "ingredient-030", "category": "ingredient", "ingredient": "파스타면"},
    ),
    Document(
        page_content="즉석밥은 전자레인지로 데우기만 하면 되어 모든 조리환경에서 가장 손쉽게 쓸 수 있는 "
        "주식 재료입니다. 볶음밥 베이스로도 활용할 수 있지만 가스레인지가 필요합니다.",
        metadata={"id": "ingredient-031", "category": "ingredient", "ingredient": "즉석밥"},
    ),
    Document(
        page_content="토마토소스는 개봉 후 냉장 보관하며 며칠 내 사용하는 것이 좋습니다. 파스타, 오븐 "
        "베이크, 스튜 베이스로 두루 활용되며 양파·마늘과 함께 볶으면 풍미가 깊어집니다.",
        metadata={"id": "ingredient-032", "category": "ingredient", "ingredient": "토마토소스"},
    ),
    Document(
        page_content="발사믹식초는 상온 보관이 가능하며 유통기한이 길어 급하게 소진할 필요가 없는 "
        "재료입니다. 샐러드 드레싱, 고기 마리네이드, 졸여서 소스로 활용할 수 있습니다.",
        metadata={"id": "ingredient-033", "category": "ingredient", "ingredient": "발사믹식초"},
    ),
    Document(
        page_content="시금치는 무르기 쉬워 신문지에 싸서 냉장 보관하고 2~3일 내 사용하는 것이 좋습니다. "
        "데쳐서 무침으로, 또는 볶음·국물 요리에 넣어 익히면 부피가 줄어 더 많이 먹을 수 있습니다.",
        metadata={"id": "ingredient-034", "category": "ingredient", "ingredient": "시금치"},
    ),
    Document(
        page_content="콩나물은 냉장 보관 시 물에 담가두면 신선도가 오래 유지됩니다. 콩나물국, 무침, "
        "볶음에 두루 쓰이고 빠르게 무르므로 구매 후 2~3일 내 사용하는 것이 좋습니다.",
        metadata={"id": "ingredient-035", "category": "ingredient", "ingredient": "콩나물"},
    ),
    Document(
        page_content="새우는 손질된 냉동 새우를 쟁여두면 활용도가 높습니다. 볶음, 찜, 파스타, 국물 "
        "요리에 두루 어울리고 해동 후에는 빨리 조리해서 먹는 것이 좋습니다.",
        metadata={"id": "ingredient-036", "category": "ingredient", "ingredient": "새우"},
    ),
    Document(
        page_content="멸치(국물용)는 건조 상태로 실온이나 냉동 보관하며 오래 둘 수 있습니다. 국물 요리의 "
        "기본 육수 재료로 쓰이고, 볶음용 잔멸치는 마른 반찬으로도 활용됩니다.",
        metadata={"id": "ingredient-037", "category": "ingredient", "ingredient": "멸치"},
    ),
    Document(
        page_content="미역은 건조 상태로 오래 보관 가능하며, 물에 불려서 미역국이나 미역무침에 씁니다. "
        "건조 상태라 유통기한 임박 걱정이 거의 없는 재료입니다.",
        metadata={"id": "ingredient-038", "category": "ingredient", "ingredient": "미역"},
    ),
    # ── 재료 대체 (substitute) ──────────────────────────────────────
    Document(
        page_content="우유가 없을 때는 두유나 물로 대체할 수 있습니다. "
        "크림 소스나 빵 반죽에는 대신, 단순히 농도를 맞추는 용도라면 물로도 대체 가능합니다.",
        metadata={"id": "substitute-001", "category": "substitute", "from": "우유", "to": "두유/물"},
    ),
    Document(
        page_content="버터가 없을 때는 식용유로 대체할 수 있습니다. "
        "식용유로 대체하면 풍미는 다소 떨어지지만 조리에는 큰 문제가 없습니다.",
        metadata={"id": "substitute-002", "category": "substitute", "from": "버터", "to": "식용유/마가린"},
    ),
    Document(
        page_content="설탕이 없을 때는 꿀이나 시럽으로 대체할 수 있습니다. "
        "꿀과 시럽은 설탕보다 단맛이 강하므로 양을 약간 줄여서 사용하는 것이 좋습니다.",
        metadata={"id": "substitute-003", "category": "substitute", "from": "설탕", "to": "꿀/시럽"},
    ),
    Document(
        page_content="고추장이 없을 때는 된장과 고춧가루, 약간의 설탕을 섞어 비슷한 맛을 낼 수 있습니다. "
        "비율은 된장 2, 고춧가루 1, 설탕 0.5 정도가 적당합니다.",
        metadata={"id": "substitute-004", "category": "substitute", "from": "고추장", "to": "된장+고춧가루"},
    ),
    Document(
        page_content="식초가 없을 때는 레몬즙으로 대체할 수 있습니다. 신맛의 강도가 비슷해 무침이나 "
        "드레싱에 1:1 비율로 대체하기 좋습니다.",
        metadata={"id": "substitute-005", "category": "substitute", "from": "식초", "to": "레몬즙"},
    ),
    Document(
        page_content="미린이 없을 때는 설탕과 청주(또는 맛술)를 섞어 비슷한 단맛과 향을 낼 수 있습니다. "
        "일식 조림이나 양념에 자주 쓰는 대체법입니다.",
        metadata={"id": "substitute-006", "category": "substitute", "from": "미린", "to": "설탕+청주"},
    ),
    Document(
        page_content="참기름이 없을 때는 들기름으로 대체할 수 있습니다. 향은 다르지만 마지막에 풍미를 "
        "더하는 용도로는 비슷하게 활용할 수 있습니다.",
        metadata={"id": "substitute-007", "category": "substitute", "from": "참기름", "to": "들기름"},
    ),
    Document(
        page_content="마요네즈가 없을 때는 그릭요거트로 대체하면 더 산뜻하고 단백질이 높은 버전이 됩니다. "
        "샐러드 드레싱이나 소스에 1:1로 대체하기 좋습니다.",
        metadata={"id": "substitute-008", "category": "substitute", "from": "마요네즈", "to": "그릭요거트"},
    ),
    Document(
        page_content="빵가루가 없을 때는 으깬 크래커나 식은 밥을 잘게 부숴 대체할 수 있습니다. 튀김이나 "
        "그라탕의 바삭한 토핑 용도로 비슷하게 활용 가능합니다.",
        metadata={"id": "substitute-009", "category": "substitute", "from": "빵가루", "to": "으깬 크래커/밥"},
    ),
    Document(
        page_content="파스타면이 없을 때는 우동면이나 당면으로 대체할 수 있습니다. 식감은 다르지만 "
        "소스를 활용하는 면 요리라면 무리 없이 대체 가능합니다.",
        metadata={"id": "substitute-010", "category": "substitute", "from": "파스타면", "to": "우동면/당면"},
    ),
    Document(
        page_content="우유가 없을 때 크림 소스를 만들어야 한다면 코코넛밀크로도 대체할 수 있습니다. "
        "단, 코코넛 향이 더해지므로 양식보다는 동남아식 요리에 더 잘 어울립니다.",
        metadata={"id": "substitute-011", "category": "substitute", "from": "우유", "to": "코코넛밀크"},
    ),
    Document(
        page_content="된장이 부족할 때는 쌈장으로 농도와 짠맛을 보완할 수 있습니다. 단맛이 더해지므로 "
        "양을 조절해서 사용하는 것이 좋습니다.",
        metadata={"id": "substitute-012", "category": "substitute", "from": "된장", "to": "쌈장"},
    ),
    Document(
        page_content="치즈가 없을 때 그라탕이나 베이크 요리에는 두유 베이스 화이트소스로 대체할 수 "
        "있습니다. 녹는 식감은 떨어지지만 고소한 맛은 어느 정도 살릴 수 있습니다.",
        metadata={"id": "substitute-013", "category": "substitute", "from": "치즈", "to": "두유 화이트소스"},
    ),
    Document(
        page_content="김치가 없을 때 비슷한 새콤한 맛을 내려면 피클이나 단무지를 활용할 수 있지만, "
        "용도가 다르므로 김치찌개·김치볶음밥처럼 김치가 핵심인 메뉴 자체를 대체하기는 어렵습니다.",
        metadata={"id": "substitute-014", "category": "substitute", "from": "김치", "to": "피클/단무지(용도 다름)"},
    ),
    Document(
        page_content="간장이 부족할 때는 진한 소금물에 약간의 설탕을 더해 간을 맞출 수 있지만, 색과 "
        "감칠맛은 떨어지므로 가능하면 간장을 보충하는 것이 좋습니다.",
        metadata={"id": "substitute-015", "category": "substitute", "from": "간장", "to": "소금물+설탕(임시방편)"},
    ),
    # ── 유통기한 임박 활용 (expiring) ───────────────────────────────
    Document(
        page_content="유통기한이 임박한 두부, 계란, 고기류는 같이 조리를 통해 안전하게 섭취하는 것이 좋습니다. "
        "부침, 볶음, 조림 등 충분히 익히는 조리법을 우선 추천합니다.",
        metadata={"id": "expiring-001", "category": "expiring", "target": "protein"},
    ),
    Document(
        page_content="유통기한이 임박한 채소는 국물 요리나 볶음에 넣어 익히면 신선도와 무관하게 맛있게 섭취할 수 있습니다. "
        "특히 양이 줄거나 시들었으면 무침으로 활용하기도 좋습니다.",
        metadata={"id": "expiring-002", "category": "expiring", "target": "vegetable"},
    ),
    Document(
        page_content="유통기한이 임박한 우유·치즈·요거트 같은 유제품은 그라탕, 크림 소스, 스무디 등 "
        "가열하거나 다른 재료와 섞는 요리에 빨리 소진하는 것이 안전합니다.",
        metadata={"id": "expiring-003", "category": "expiring", "target": "dairy"},
    ),
    Document(
        page_content="유통기한이 임박한 즉석밥이나 밥류는 볶음밥, 죽, 누룽지로 만들면 식감 변화 없이 "
        "활용할 수 있습니다. 밥은 다른 재료보다 변질 속도가 느려 급하지 않은 편입니다.",
        metadata={"id": "expiring-004", "category": "expiring", "target": "grain"},
    ),
    Document(
        page_content="유통기한이 임박한 새우·해산물은 충분히 익혀서 볶음이나 찜, 국물 요리로 바로 "
        "소진하는 것이 안전합니다. 해산물은 상온에 오래 두면 빠르게 변질되니 주의가 필요합니다.",
        metadata={"id": "expiring-005", "category": "expiring", "target": "seafood"},
    ),
    Document(
        page_content="유통기한이 임박한 과일류는 그대로 먹기 애매하면 잘라서 샐러드나 소스, 디저트 "
        "토핑으로 활용하면 낭비 없이 소진할 수 있습니다.",
        metadata={"id": "expiring-006", "category": "expiring", "target": "fruit"},
    ),
    # ── 음식 취향 (preference) ──────────────────────────────────────
    Document(
        page_content="한식(korean)은 밥, 국/찌개, 반찬으로 구성되는 경우가 많으며 간장, 고추장, 된장, 마늘, 두부 등을 "
        "기본 양념으로 활용합니다. 볶음, 조림, 찌개류가 대표적입니다.",
        metadata={"id": "preference-001", "category": "preference", "preference": "korean"},
    ),
    Document(
        page_content="한식 대표 메뉴 예시: 김치찌개, 된장찌개, 계란말이, 제육볶음, 미역국, 콩나물무침. "
        "재료 본연의 맛을 살리면서 양념으로 감칠맛을 더하는 방식이 특징입니다.",
        metadata={"id": "preference-002", "category": "preference", "preference": "korean"},
    ),
    Document(
        page_content="한식 조리에 자주 쓰이는 재료는 대파, 마늘, 고춧가루, 참기름, 들기름이며, 국물 "
        "요리에는 멸치나 다시마로 육수를 내는 경우가 많습니다.",
        metadata={"id": "preference-003", "category": "preference", "preference": "korean"},
    ),
    Document(
        page_content="양식(western)은 파스타, 스테이크, 샐러드, 수프 등이 대표적이며 올리브오일, 버터, 치즈, "
        "토마토소스 등을 활용합니다. 오븐이나 프라이팬을 이용한 조리가 많습니다.",
        metadata={"id": "preference-004", "category": "preference", "preference": "western"},
    ),
    Document(
        page_content="양식 대표 메뉴 예시: 토마토파스타, 크림파스타, 아스파라거스 구이, 그라탕, "
        "치즈오믈렛. 소스를 베이스로 풍미를 쌓아가는 조리 방식이 특징입니다.",
        metadata={"id": "preference-005", "category": "preference", "preference": "western"},
    ),
    Document(
        page_content="양식에 자주 쓰이는 재료는 올리브오일, 발사믹식초, 치즈, 버터, 마늘이며, 허브류 "
        "(바질, 로즈마리)가 있으면 풍미를 크게 높일 수 있습니다.",
        metadata={"id": "preference-006", "category": "preference", "preference": "western"},
    ),
    Document(
        page_content="일식(japanese)은 된장국(미소시루), 덮밥, 야끼니쿠, 우동 등이 대표적이며 간장, 미린, "
        "가쓰오부시 등을 양념으로 활용합니다. 비교적 간단한 조리법이 많아 1인 가구에 적합합니다.",
        metadata={"id": "preference-007", "category": "preference", "preference": "japanese"},
    ),
    Document(
        page_content="일식 대표 메뉴 예시: 계란덮밥(타마고동), 우동, 미소시루, 데리야끼 닭가슴살. "
        "단짠 양념(간장+미린+설탕)을 기본으로 깔끔하게 조리하는 것이 특징입니다.",
        metadata={"id": "preference-008", "category": "preference", "preference": "japanese"},
    ),
    Document(
        page_content="일식 조리에 자주 쓰이는 재료는 간장, 미린, 가쓰오부시, 미소(된장과 유사), 대파이며 "
        "조리 시간이 짧고 재료 손질이 간단한 것이 특징입니다.",
        metadata={"id": "preference-009", "category": "preference", "preference": "japanese"},
    ),
    Document(
        page_content="고단백(highprotein) 식단은 닭가슴살, 계란, 두부, 그릭요거트 등 단백질 함량이 높은 재료를 활용한 "
        "요리를 우선 추천합니다. 튀김보다는 구이, 찜, 삶기 등 기름을 적게 쓰는 조리법이 좋습니다.",
        metadata={"id": "preference-010", "category": "preference", "preference": "highprotein"},
    ),
    Document(
        page_content="고단백 식단 대표 메뉴 예시: 닭가슴살 스테이크, 계란찜, 두부조림, 그릭요거트 "
        "샐러드. 양념은 최소화하고 재료 자체의 단백질을 살리는 조리법을 우선합니다.",
        metadata={"id": "preference-011", "category": "preference", "preference": "highprotein"},
    ),
    Document(
        page_content="고단백 식단에서는 전자레인지·찜 조리로도 충분히 메뉴를 구성할 수 있습니다(닭가슴살 "
        "찜, 계란찜). 조리 도구가 제한적인 환경에서도 고단백 식단 구성이 가능합니다.",
        metadata={"id": "preference-012", "category": "preference", "preference": "highprotein"},
    ),
    Document(
        page_content="음식 취향이 'none'(제한없음)이면 특정 스타일에 얽매이지 않고 보유 재료와 조리환경에 "
        "가장 잘 맞는 메뉴를 자유롭게 추천하면 됩니다.",
        metadata={"id": "preference-013", "category": "preference", "preference": "none"},
    ),
    Document(
        page_content="'none' 취향에서는 한식·양식·일식을 섞어도 무방하며, 재료 활용도와 조리 난이도를 "
        "우선 기준으로 삼아 추천하는 것이 좋습니다.",
        metadata={"id": "preference-014", "category": "preference", "preference": "none"},
    ),
    # ── 조리환경 × 음식취향 조합 (combo) ────────────────────────────
    Document(
        page_content="전자레인지 환경에서 한식을 만들 때는 계란찜, 두부계란찜, 단호박찜처럼 찜 형태의 "
        "메뉴가 한식 풍미(간장, 참기름)를 살리면서도 조리 제약을 지킬 수 있는 조합입니다.",
        metadata={"id": "combo-001", "category": "combo", "env": "microwave", "preference": "korean"},
    ),
    Document(
        page_content="전자레인지 환경에서 양식을 만들 때는 오븐 없이도 되는 메뉴가 제한적입니다. 치즈를 "
        "올린 계란찜이나 데운 그릭요거트+과일 정도로 양식 풍미를 살짝 가져오는 수준이 현실적입니다.",
        metadata={"id": "combo-002", "category": "combo", "env": "microwave", "preference": "western"},
    ),
    Document(
        page_content="전자레인지 환경에서 일식을 만들 때는 계란덮밥(전자레인지로 계란을 익혀 즉석밥에 "
        "올리는 방식)이나 미소시루를 데우는 정도로 구성하면 조리 제약 안에서 일식 느낌을 낼 수 있습니다.",
        metadata={"id": "combo-003", "category": "combo", "env": "microwave", "preference": "japanese"},
    ),
    Document(
        page_content="전자레인지 환경에서 고단백 식단을 만들 때는 닭가슴살찜, 계란찜, 두부찜이 핵심 "
        "메뉴입니다. 모두 내열용기에 재료를 넣고 익히는 찜 방식으로 단백질을 충분히 챙길 수 있습니다.",
        metadata={"id": "combo-004", "category": "combo", "env": "microwave", "preference": "highprotein"},
    ),
    Document(
        page_content="가스레인지 1구 환경에서 한식을 만들 때는 찌개, 볶음, 전 모두 냄비/프라이팬 하나로 "
        "끝낼 수 있어 가장 잘 맞는 조합입니다. 김치찌개, 제육볶음, 계란말이가 대표적입니다.",
        metadata={"id": "combo-005", "category": "combo", "env": "oneburner", "preference": "korean"},
    ),
    Document(
        page_content="가스레인지 1구 환경에서 양식을 만들 때는 파스타(면을 삶고 같은 냄비나 다른 팬에서 "
        "소스를 볶는 방식)가 가장 현실적입니다. 오븐이 필요한 그라탕류는 추천하기 어렵습니다.",
        metadata={"id": "combo-006", "category": "combo", "env": "oneburner", "preference": "western"},
    ),
    Document(
        page_content="가스레인지 1구 환경에서 일식을 만들 때는 우동(국물우동, 볶음우동)이나 계란덮밥이 "
        "냄비/프라이팬 하나로 완성되어 잘 맞습니다.",
        metadata={"id": "combo-007", "category": "combo", "env": "oneburner", "preference": "japanese"},
    ),
    Document(
        page_content="가스레인지 1구 환경에서 고단백 식단을 만들 때는 닭가슴살을 삶거나 구워 메인으로 "
        "쓰고, 계란/두부를 곁들이는 한 그릭 구성이 적합합니다.",
        metadata={"id": "combo-008", "category": "combo", "env": "oneburner", "preference": "highprotein"},
    ),
    Document(
        page_content="풀옵션 환경에서 한식을 만들 때는 찌개·볶음뿐 아니라 오븐을 활용한 갈비찜, "
        "에어프라이어 치킨까지 폭넓게 추천할 수 있습니다.",
        metadata={"id": "combo-009", "category": "combo", "env": "full", "preference": "korean"},
    ),
    Document(
        page_content="풀옵션 환경에서 양식을 만들 때는 오븐 그라탕, 파스타 베이크, 스테이크, 아스파라거스 "
        "구이까지 다양한 조리 도구를 활용한 코스 요리가 가능합니다.",
        metadata={"id": "combo-010", "category": "combo", "env": "full", "preference": "western"},
    ),
    Document(
        page_content="풀옵션 환경에서 일식을 만들 때는 데리야끼 치킨, 오븐으로 굽는 사케구이까지 "
        "가능해 가스레인지 1구보다 메뉴 폭이 훨씬 넓어집니다.",
        metadata={"id": "combo-011", "category": "combo", "env": "full", "preference": "japanese"},
    ),
    Document(
        page_content="풀옵션 환경에서 고단백 식단을 만들 때는 에어프라이어 닭가슴살, 오븐 구이 생선/고기, "
        "그릭요거트 디저트까지 조리 도구 제약 없이 다양하게 구성할 수 있습니다.",
        metadata={"id": "combo-012", "category": "combo", "env": "full", "preference": "highprotein"},
    ),
    # ── 가구 규모별 팁 (household) ──────────────────────────────────
    Document(
        page_content="1인 가구는 한 번에 1~2인분만 조리하는 것이 좋고, 재료를 소분해서 냉동하면 "
        "유통기한 임박 재료가 자주 남는 문제를 줄일 수 있습니다.",
        metadata={"id": "household-001", "category": "household", "type": "single"},
    ),
    Document(
        page_content="3~4인 가족 가구는 한 번에 여러 끼를 해결할 수 있는 찌개·볶음류처럼 양을 늘리기 "
        "쉬운 메뉴가 효율적입니다. 국물 요리는 양을 늘려도 맛의 변화가 적습니다.",
        metadata={"id": "household-002", "category": "household", "type": "family"},
    ),
    Document(
        page_content="5인 이상 대가구는 한 번에 많은 양을 조리해야 하므로, 큰 냄비/팬으로 한 번에 "
        "조리되는 찌개·볶음밥·전 같은 메뉴가 1인 가구 메뉴보다 효율적입니다.",
        metadata={"id": "household-003", "category": "household", "type": "family_large"},
    ),
]


def build_vectorstore(embeddings: Embeddings) -> FAISS:
    """조리 지식 코퍼스에 대한 FAISS 벡터스토어를 만듭니다.

    FAISS_INDEX_DIR에 저장된 인덱스가 있고 문서 수가 COOKING_KNOWLEDGE와 일치하면
    그걸 그대로 불러와서 임베딩 API 호출을 건너뜁니다(코퍼스를 고친 뒤 재배포 전에
    `python -m naengchae_chain.knowledge_base`로 인덱스를 다시 만들어야 합니다 — 문서
    개수가 다르면 자동으로 다시 빌드하지만, 내용만 바뀐 경우는 감지하지 못합니다).
    """
    if FAISS_INDEX_DIR.exists():
        try:
            vectorstore = FAISS.load_local(
                str(FAISS_INDEX_DIR), embeddings, allow_dangerous_deserialization=True
            )
            if vectorstore.index.ntotal == len(COOKING_KNOWLEDGE):
                return vectorstore
        except Exception:
            pass  # 손상되거나 호환 안 되는 캐시 - 아래에서 새로 빌드

    vectorstore = FAISS.from_documents(COOKING_KNOWLEDGE, embeddings)
    vectorstore.save_local(str(FAISS_INDEX_DIR))
    return vectorstore


if __name__ == "__main__":
    # 코퍼스를 고친 뒤 인덱스 캐시를 다시 만들 때 직접 실행하는 진입점입니다.
    #   cd naengchae-langchain && source .venv/bin/activate
    #   python -m naengchae_chain.knowledge_base
    import shutil

    from dotenv import load_dotenv
    from langchain_upstage import UpstageEmbeddings

    load_dotenv(PACKAGE_ROOT / ".env")
    if FAISS_INDEX_DIR.exists():
        shutil.rmtree(FAISS_INDEX_DIR)
    embeddings = UpstageEmbeddings(model="solar-embedding-1-large")
    build_vectorstore(embeddings)
    print(f"FAISS 인덱스 {len(COOKING_KNOWLEDGE)}개 문서 -> {FAISS_INDEX_DIR}에 저장 완료")


def build_retriever(embeddings: Embeddings, k: int = 4) -> VectorStoreRetriever:
    """조리 지식 코퍼스에 대한 retriever를 만듭니다."""
    return build_vectorstore(embeddings).as_retriever(search_kwargs={"k": k})
