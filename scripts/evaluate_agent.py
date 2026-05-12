"""
Evaluation script for the EcoMarket router and return agent.

By default this script evaluates only router classification, which does not call
Gemini. Use --live to execute full RAG/agent flows and inspect tool calls.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from customer_service_router import classify_customer_intent, handle_customer_message


PROJECT_ROOT = Path(__file__).parent.parent
EVALUATION_DIR = PROJECT_ROOT / "evaluation"
TEST_CASES_PATH = EVALUATION_DIR / "agent_test_cases.json"
RESULTS_PATH = EVALUATION_DIR / "agent_results.json"


def load_test_cases() -> List[Dict[str, Any]]:
    """Load agent/router test cases from disk."""
    if not TEST_CASES_PATH.exists():
        raise FileNotFoundError(f"Missing test cases file: {TEST_CASES_PATH}")

    with open(TEST_CASES_PATH, "r", encoding="utf-8") as file:
        return json.load(file)["cases"]


def _tool_call_names(result: Dict[str, Any]) -> List[str]:
    """Extract tool-call names from a live router result."""
    return [
        event.get("name")
        for event in result.get("tool_trace", [])
        if event.get("event") == "tool_call"
    ]


def _tool_result_text(result: Dict[str, Any]) -> str:
    """Join tool-result payloads into a searchable text block."""
    return "\n".join(
        str(event.get("content", ""))
        for event in result.get("tool_trace", [])
        if event.get("event") == "tool_result"
    )


def evaluate_case(case: Dict[str, Any], live: bool) -> Dict[str, Any]:
    """Evaluate a single test case in classification-only or live mode."""
    started_at = time.time()
    classification = classify_customer_intent(case["message"])

    entry: Dict[str, Any] = {
        "id": case["id"],
        "category": case["category"],
        "message": case["message"],
        "expected_route": case["expected_route"],
        "actual_route": classification["route"],
        "route_correct": classification["route"] == case["expected_route"],
        "classification": classification,
        "live": live,
    }

    if live:
        result = handle_customer_message(case["message"])
        actual_tools = _tool_call_names(result)
        expected_tools = case.get("expected_tools", [])
        tool_results_text = _tool_result_text(result)

        entry.update({
            "answer": result.get("answer", ""),
            "actual_route": result.get("route"),
            "route_correct": result.get("route") == case["expected_route"],
            "expected_tools": expected_tools,
            "actual_tools": actual_tools,
            "tools_correct": all(tool_name in actual_tools for tool_name in expected_tools),
            "expected_error_code": case.get("expected_error_code"),
            "error_code_found": (
                case.get("expected_error_code") in tool_results_text
                if case.get("expected_error_code")
                else None
            ),
            "expected_label_generated": case.get("expected_label_generated"),
            "label_generation_found": (
                "label_generated\": true" in tool_results_text
                if case.get("expected_label_generated") is not None
                else None
            ),
        })

    entry["elapsed_seconds"] = round(time.time() - started_at, 2)
    return entry


def summarize_results(results: List[Dict[str, Any]], live: bool) -> Dict[str, Any]:
    """Compute aggregate evaluation metrics."""
    total = len(results)
    route_correct = sum(1 for result in results if result["route_correct"])
    summary = {
        "evaluation_date": datetime.now().isoformat(),
        "mode": "live" if live else "classification_only",
        "total_cases": total,
        "route_accuracy_percent": round((route_correct / total * 100) if total else 0, 2),
        "route_correct": route_correct,
    }

    if live:
        cases_with_tools = [
            result for result in results
            if "tools_correct" in result and result.get("expected_tools")
        ]
        tools_correct = sum(1 for result in cases_with_tools if result["tools_correct"])
        summary.update({
            "tool_cases": len(cases_with_tools),
            "tool_accuracy_percent": round(
                (tools_correct / len(cases_with_tools) * 100)
                if cases_with_tools else 0,
                2,
            ),
            "tools_correct": tools_correct,
        })

    return summary


def run_evaluation(live: bool, save: bool) -> Dict[str, Any]:
    """Run all configured test cases and optionally save results."""
    cases = load_test_cases()
    results = [evaluate_case(case, live=live) for case in cases]
    summary = summarize_results(results, live=live)

    payload = {
        "summary": summary,
        "results": results,
    }

    if save:
        with open(RESULTS_PATH, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)

    return payload


def _run_cli() -> None:
    """Run the evaluation command-line interface."""
    parser = argparse.ArgumentParser(description="Evaluate EcoMarket agent/router behavior")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Execute full RAG/agent flows. This calls Gemini and may use quota.",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not write evaluation/agent_results.json",
    )
    args = parser.parse_args()

    try:
        payload = run_evaluation(live=args.live, save=not args.no_save)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    if not args.no_save:
        print(f"Detailed results saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    _run_cli()
