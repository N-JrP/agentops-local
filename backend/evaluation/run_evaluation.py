import json
from datetime import datetime, timezone
from pathlib import Path

from backend.agent.graph import run_investigation
from backend.evaluation.test_cases import EVALUATION_CASES
from backend.persistence import save_evaluation_report

REPORT_DIR = Path("reports")


def _contains_all(answer: str, expected: list[str]) -> bool:
    answer_lower = answer.lower()
    return all(item.lower() in answer_lower for item in expected)


def run_evaluation() -> dict:
    rows = []

    for case in EVALUATION_CASES:
        print("=" * 80)
        print(f"TEST: {case['name']}")
        print(f"QUESTION: {case['question']}")

        result = run_investigation(case["question"])
        actual_tools = [step["tool"] for step in result["plan"]]
        expected_tools = case["expected_tools"]

        tool_set_match = set(actual_tools) == set(expected_tools)
        exact_order_match = actual_tools == expected_tools
        completeness_match = _contains_all(
            result["answer"],
            case.get("expected_answer_contains", []),
        )

        row = {
            "name": case["name"],
            "expected_tools": expected_tools,
            "actual_tools": actual_tools,
            "tool_set_match": tool_set_match,
            "exact_order_match": exact_order_match,
            "answer_valid": result["answer_valid"],
            "validation_issues": result["answer_validation_issues"],
            "answer_completeness_match": completeness_match,
            "requires_human_review": result["requires_human_review"],
            "planner_duration_ms": result["planner_duration_ms"],
            "answer_duration_ms": result["answer_duration_ms"],
            "investigation_duration_ms": result["investigation_duration_ms"],
        }
        rows.append(row)

        print(f"EXPECTED TOOLS: {expected_tools}")
        print(f"ACTUAL TOOLS:   {actual_tools}")
        print(f"TOOL SET MATCH: {tool_set_match}")
        print(f"EXACT ORDER MATCH: {exact_order_match}")
        print(f"ANSWER VALID: {result['answer_valid']}")
        print(f"VALIDATION ISSUES: {result['answer_validation_issues']}")
        print(f"ANSWER COMPLETENESS: {completeness_match}")
        print(f"HUMAN REVIEW: {result['requires_human_review']}")
        print()

    total = len(rows)
    summary = {
        "cases": total,
        "tool_set_accuracy": sum(row["tool_set_match"] for row in rows) / total,
        "exact_order_accuracy": sum(row["exact_order_match"] for row in rows) / total,
        "answer_validation_rate": sum(row["answer_valid"] for row in rows) / total,
        "answer_completeness_rate": sum(row["answer_completeness_match"] for row in rows) / total,
        "human_review_rate": sum(row["requires_human_review"] for row in rows) / total,
    }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "cases": rows,
    }

    REPORT_DIR.mkdir(exist_ok=True)
    report_path = REPORT_DIR / "evaluation_latest.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["persistence_id"] = save_evaluation_report(report, evaluation_type="offline")

    print("=" * 80)
    print("SUMMARY")
    print(json.dumps(summary, indent=2))
    print(f"Saved report: {report_path}")
    return report


if __name__ == "__main__":
    run_evaluation()
