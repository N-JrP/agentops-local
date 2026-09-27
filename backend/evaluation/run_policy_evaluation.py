import json
from pathlib import Path

from backend.agent.nodes import _required_tools_from_question
from backend.evaluation.live_policy_cases import LIVE_POLICY_CASES
from backend.evaluation.test_cases import EVALUATION_CASES


def main() -> None:
    rows = []
    for case in EVALUATION_CASES + LIVE_POLICY_CASES:
        actual = _required_tools_from_question(case["question"])
        expected = case["expected_tools"]
        rows.append(
            {
                "name": case["name"],
                "expected_tools": expected,
                "actual_tools": actual,
                "match": actual == expected,
            }
        )

    passed = sum(row["match"] for row in rows)
    report = {
        "cases": len(rows),
        "passed": passed,
        "accuracy": passed / len(rows) if rows else 1.0,
        "rows": rows,
    }
    Path("reports").mkdir(exist_ok=True)
    Path("reports/policy_evaluation.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    if passed != len(rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
