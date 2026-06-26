"""RAG 코퍼스(knowledge_base.py) retrieval 품질 평가.

eval/retrieval_cases.json의 (질의, 정답 문서 id) 쌍으로 retrieval 품질 두 가지를 측정한다.

1. 랭킹 품질 (현재 코퍼스 기준): hit@k / recall@k / MRR — k=4(현재 운영값)와 k=8을 비교해
   k를 늘리는 게 실제로 이득인지 확인한다.
2. 코퍼스 확장의 가치 (Phase 3 전/후): 각 질의가 묻는 주제가 "구버전(17~18개 문서) 코퍼스에
   원래 존재라도 했는지"를 키워드 기반으로 점검한다. 구버전 문서에는 id가 없고 일부 문서는 표현이
   완전히 바뀌어서(예: "양파와 감자" 결합 문서 -> 양파/감자 분리 문서) 정확한 id 매핑이 불가능하기
   때문에, 무리하게 id를 갖다 맞추는 대신 "이 주제에 대한 정보가 코퍼스에 존재할 가능성이 있었는가"
   라는 더 솔직한 질문으로 바꿔 측정한다. 왜 이 방식을 선택했는지는
   naengchae-langchain/eval/RETRIEVAL_EVAL.md 참고.

실행: (naengchae-langchain/.venv 활성화 후)
    python eval/run_retrieval_eval.py
"""

import json
import subprocess
import sys
import types
from collections import Counter
from datetime import datetime
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PACKAGE_ROOT.parent
sys.path.insert(0, str(PACKAGE_ROOT))

from dotenv import load_dotenv

load_dotenv(PACKAGE_ROOT / ".env")

from naengchae_chain.knowledge_base import COOKING_KNOWLEDGE, build_retriever

K_VALUES = [4, 8]

# expiring/household는 metadata 값이 영문 코드라 한글 본문과 직접 매칭되지 않으므로,
# "구버전 코퍼스에 이 주제가 있었는가"를 점검할 때만 쓰는 한글 키워드 매핑.
EXPIRING_KEYWORDS = {
    "protein": "두부, 계란, 고기류",
    "vegetable": "채소",
    "dairy": "유제품",
    "grain": "즉석밥",
    "seafood": "새우",
    "fruit": "과일",
}
HOUSEHOLD_KEYWORDS = {"single": "1인 가구", "family": "가족", "family_large": "대가구"}


def load_old_corpus_text() -> str:
    """이번 Phase 3 작업 직전(git HEAD) 시점의 knowledge_base.py에서 구버전 코퍼스 본문을 가져온다."""
    rel_path = "naengchae-langchain/naengchae_chain/knowledge_base.py"
    old_source = subprocess.run(
        ["git", "show", f"HEAD:{rel_path}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    module = types.ModuleType("old_knowledge_base")
    exec(old_source, module.__dict__)
    old_docs = module.COOKING_KNOWLEDGE
    return "\n".join(doc.page_content for doc in old_docs)


def topic_keyword(doc_id: str) -> str:
    """relevant_id 하나에서 '구버전에 이 주제가 있었는가'를 검색할 한글 키워드를 뽑는다."""
    doc = next(d for d in COOKING_KNOWLEDGE if d.metadata["id"] == doc_id)
    meta = doc.metadata
    category = meta["category"]
    if category == "ingredient":
        return meta["ingredient"]
    if category == "substitute":
        return meta["from"]
    if category == "expiring":
        return EXPIRING_KEYWORDS[meta["target"]]
    if category == "household":
        return HOUSEHOLD_KEYWORDS[meta["type"]]
    if category == "preference":
        return f"({meta['preference']})"  # 원문에 "한식(korean)"처럼 괄호로 영문 표기됨
    if category == "cookingEnv":
        return f"({meta['env']})"
    if category == "combo":
        return f"({meta['preference']})"  # combo는 일단 preference 키워드로 근사
    raise ValueError(f"알 수 없는 category: {category}")


def had_old_coverage(relevant_ids: list[str], old_text: str) -> bool:
    """이 질의의 정답 주제 중 하나라도 구버전 코퍼스 텍스트에 키워드가 등장하면 True."""
    return any(topic_keyword(doc_id) in old_text for doc_id in relevant_ids)


def evaluate_ranking(cases: list[dict], k: int) -> dict:
    embeddings_retriever = build_retriever(_EMBEDDINGS, k=k)

    hits, recalls, ranks = [], [], []
    for case in cases:
        docs = embeddings_retriever.invoke(case["query"])
        retrieved_ids = [d.metadata["id"] for d in docs]
        relevant = set(case["relevant_ids"])

        hit = 1 if relevant & set(retrieved_ids) else 0
        recall = len(relevant & set(retrieved_ids)) / len(relevant)
        rank = next(
            (i + 1 for i, rid in enumerate(retrieved_ids) if rid in relevant), None
        )

        hits.append(hit)
        recalls.append(recall)
        ranks.append(1 / rank if rank else 0.0)

    return {
        "k": k,
        "hit_rate": round(sum(hits) / len(hits), 3),
        "recall": round(sum(recalls) / len(recalls), 3),
        "mrr": round(sum(ranks) / len(ranks), 3),
    }


def evaluate_coverage_gap(cases: list[dict], old_text: str) -> dict:
    covered = [had_old_coverage(c["relevant_ids"], old_text) for c in cases]
    return {
        "total_queries": len(cases),
        "old_corpus_covered": sum(covered),
        "old_corpus_uncovered": len(covered) - sum(covered),
        "coverage_rate_old": round(sum(covered) / len(covered), 3),
        "uncovered_query_ids": [c["id"] for c, cov in zip(cases, covered) if not cov],
    }


def main() -> None:
    global _EMBEDDINGS
    from langchain_upstage import UpstageEmbeddings

    _EMBEDDINGS = UpstageEmbeddings(model="solar-embedding-1-large")

    cases = json.loads((PACKAGE_ROOT / "eval" / "retrieval_cases.json").read_text(encoding="utf-8"))

    print("=" * 60)
    print(f"RAG 코퍼스 retrieval 평가 (현재 코퍼스 {len(COOKING_KNOWLEDGE)}개 문서, 질의 {len(cases)}건)")
    print("=" * 60)

    ranking_results = [evaluate_ranking(cases, k) for k in K_VALUES]
    for r in ranking_results:
        print(f"k={r['k']:>2}: hit_rate={r['hit_rate']}  recall={r['recall']}  MRR={r['mrr']}")

    old_text = load_old_corpus_text()
    coverage = evaluate_coverage_gap(cases, old_text)
    print()
    print("구버전 코퍼스(Phase 3 이전) 대비 주제 커버리지:")
    print(
        f"  전체 {coverage['total_queries']}건 중 구버전에 주제가 존재했던 질의: "
        f"{coverage['old_corpus_covered']}건 ({coverage['coverage_rate_old'] * 100:.1f}%)"
    )
    print(
        f"  구버전에 아예 없던(=Phase 3 확장으로 새로 커버된) 질의: "
        f"{coverage['old_corpus_uncovered']}건"
    )
    print(f"  새로 커버된 질의 id: {coverage['uncovered_query_ids']}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = PACKAGE_ROOT / "eval" / "results" / f"retrieval_run_{timestamp}.json"
    out_path.write_text(
        json.dumps(
            {"ranking": ranking_results, "coverage_gap": coverage},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n결과 저장: {out_path}")


if __name__ == "__main__":
    main()
