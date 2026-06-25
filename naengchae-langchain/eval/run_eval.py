"""냉채 레시피 추천 에이전트 평가 하니스.

eval/cases.json의 합성 테스트케이스를 recommend_recipes_agent에 실제로 통과시켜
1차 통과율, 최종 통과율, 평균 재시도 횟수, 실패 유형 분포를 측정합니다.

실행: (naengchae-langchain/.venv 활성화 후, naengchae-langchain/.env에 UPSTAGE_API_KEY 필요)
    python eval/run_eval.py
"""

import json
import re
import sys
import time
from collections import Counter
from datetime import date, datetime
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PACKAGE_ROOT))

from dotenv import load_dotenv

load_dotenv(PACKAGE_ROOT / ".env")

from naengchae_chain.graph import recommend_recipes_agent
from naengchae_chain.knowledge_base import build_retriever
from naengchae_chain.models import FridgeIngredient, UserProfile

ISSUE_PATTERNS: list[tuple[str, str]] = [
    (r"환경에서는.*조리법을 추천할 수 없습니다", "forbidden_cooking_method"),
    (r"보유 재료 목록에 없습니다", "ingredient_not_in_fridge"),
    (r"usesExpiringIngredient가 true이지만", "expiring_flag_false_positive"),
    (r"유통기한 임박 재료\(.*\)를 사용하는 레시피가", "expiring_ingredient_unused"),
]


def categorize_issue(line: str) -> str:
    for pattern, label in ISSUE_PATTERNS:
        if re.search(pattern, line):
            return label
    return "other"


def load_cases(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_case(llm, retriever, case: dict) -> dict:
    profile = UserProfile(**case["profile"])
    ingredients = [FridgeIngredient(**ing) for ing in case["ingredients"]]
    today = date.fromisoformat(case["today"]) if case.get("today") else date.today()

    start = time.perf_counter()
    try:
        recommendation, final_state = recommend_recipes_agent(
            llm, retriever, profile, ingredients, today
        )
        elapsed = time.perf_counter() - start
        issues = [line for line in final_state["feedback"].split("\n") if line.strip()]
        categories = sorted({categorize_issue(line) for line in issues}) if issues else []
        return {
            "id": case["id"],
            "description": case["description"],
            "error": None,
            "valid": final_state["valid"],
            "retry_count": final_state["retry_count"],
            "issue_categories": categories,
            "issues": issues,
            "recipe_names": [r.name for r in recommendation.recipes],
            "elapsed_seconds": round(elapsed, 2),
        }
    except Exception as e:
        elapsed = time.perf_counter() - start
        return {
            "id": case["id"],
            "description": case["description"],
            "error": f"{type(e).__name__}: {e}",
            "valid": False,
            "retry_count": None,
            "issue_categories": ["exception"],
            "issues": [],
            "recipe_names": [],
            "elapsed_seconds": round(elapsed, 2),
        }


def summarize(results: list[dict]) -> dict:
    total = len(results)
    errored = [r for r in results if r["error"] is not None]
    scored = [r for r in results if r["error"] is None]

    final_pass = sum(1 for r in scored if r["valid"])
    first_try_pass = sum(1 for r in scored if r["valid"] and r["retry_count"] == 0)
    avg_retries = (
        sum(r["retry_count"] for r in scored) / len(scored) if scored else 0.0
    )
    retry_distribution = Counter(r["retry_count"] for r in scored)

    failure_categories = Counter()
    for r in results:
        if not r["valid"]:
            for cat in r["issue_categories"]:
                failure_categories[cat] += 1

    avg_latency = sum(r["elapsed_seconds"] for r in results) / total if total else 0.0

    return {
        "total_cases": total,
        "errored_cases": len(errored),
        "final_pass_rate": round(final_pass / total, 3) if total else 0.0,
        "first_try_pass_rate": round(first_try_pass / total, 3) if total else 0.0,
        "avg_retry_count": round(avg_retries, 2),
        "retry_distribution": dict(sorted(retry_distribution.items())),
        "failure_categories": dict(failure_categories.most_common()),
        "avg_latency_seconds": round(avg_latency, 2),
    }


def print_report(summary: dict, results: list[dict]) -> None:
    print("=" * 60)
    print("냉채 레시피 추천 에이전트 평가 결과")
    print("=" * 60)
    print(f"총 케이스: {summary['total_cases']}건 (예외 발생: {summary['errored_cases']}건)")
    print(f"최종 통과율: {summary['final_pass_rate'] * 100:.1f}%")
    print(f"1차 통과율 (재시도 없이 통과): {summary['first_try_pass_rate'] * 100:.1f}%")
    print(f"평균 재시도 횟수: {summary['avg_retry_count']}")
    print(f"재시도 횟수 분포: {summary['retry_distribution']}")
    print(f"평균 응답 시간: {summary['avg_latency_seconds']}초")
    print()
    print("실패 유형 분포 (실패 케이스 1건이 여러 유형에 중복 집계될 수 있음):")
    if summary["failure_categories"]:
        for cat, count in summary["failure_categories"].items():
            print(f"  - {cat}: {count}건")
    else:
        print("  (없음 - 전부 통과)")
    print()
    print("케이스별 결과:")
    for r in results:
        status = "PASS" if r["valid"] else "FAIL"
        retry_info = f"retry={r['retry_count']}" if r["retry_count"] is not None else "ERROR"
        print(f"  [{status}] {r['id']:30s} {retry_info:12s} {r['elapsed_seconds']}s")
        if r["error"]:
            print(f"           ! {r['error']}")
        elif not r["valid"]:
            for issue in r["issues"]:
                print(f"           - {issue}")


def main() -> None:
    from langchain_upstage import ChatUpstage, UpstageEmbeddings

    embeddings = UpstageEmbeddings(model="solar-embedding-1-large")
    retriever = build_retriever(embeddings, k=4)
    llm = ChatUpstage(model="solar-pro3", temperature=0)

    cases = load_cases(PACKAGE_ROOT / "eval" / "cases.json")
    results = [run_case(llm, retriever, case) for case in cases]
    summary = summarize(results)

    print_report(summary, results)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = PACKAGE_ROOT / "eval" / "results" / f"run_{timestamp}.json"
    out_path.write_text(
        json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n결과 저장: {out_path}")


if __name__ == "__main__":
    main()
