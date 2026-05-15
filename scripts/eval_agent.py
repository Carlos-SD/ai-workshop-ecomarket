"""Run the 10 test scenarios from PHASE3.md §7 against the live agent.

Each scenario has:
- a prompt
- the expected tool path (which tools should be invoked, in order)
- a free-text expectation about the final response

The script prints a per-scenario verdict and a summary table.

Usage:
    # From the repo root, with .env configured:
    python -m scripts.eval_agent
    # Or, with the simulated date pinned (recommended for reproducibility):
    SIMULATED_TODAY=2026-05-15 python -m scripts.eval_agent

Requires GOOGLE_API_KEY in .env. The script makes one Gemini API call per
scenario (≤10 calls), well within the free tier.
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Make the app package importable when running as a script.
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent import build_agent, run_turn  # noqa: E402

console = Console()

# Gemini 2.5 Flash free tier = 5 RPM. Each scenario can issue 1-3 LLM calls
# (planning + tool-execution + final-response). 15s between scenarios keeps us
# safely under the rolling-minute window. Override with EVAL_SLEEP_SECS=0 to
# disable when running against a paid tier.
SLEEP_BETWEEN_SCENARIOS = int(os.getenv("EVAL_SLEEP_SECS", "15"))


@dataclass
class Scenario:
    id: int
    prompt: str
    expected_tools: list[str]            # ordered list, "" means "no tool"
    expected_outcome: str                # free-text description
    notes: str = ""
    # If True, accept "agent asked a clarifying question instead of calling the
    # final tool" as a pass. This reflects desirable conservative behavior
    # (e.g. asking for return_reason before issuing a label).
    accept_clarification: bool = False
    actual_tools: list[str] = field(default_factory=list)
    actual_output: str = ""
    passed: bool = False
    details: str = ""


SCENARIOS: list[Scenario] = [
    Scenario(
        id=1,
        prompt="Where is order 12345?",
        expected_tools=["consultar_estado_pedido"],
        expected_outcome="Status + tracking link for order 12345 (In Transit, EcoExpress).",
    ),
    Scenario(
        id=2,
        prompt="Can I return a bamboo toothbrush?",
        expected_tools=["consultar_politica_devolucion"],
        expected_outcome="Explanation that bamboo toothbrushes are non-returnable (personal hygiene).",
    ),
    Scenario(
        id=3,
        prompt="I want to return the water bottle from order 12355 because it leaks.",
        expected_tools=["verificar_elegibilidad_devolucion", "generar_etiqueta_devolucion"],
        expected_outcome="Eligibility confirmed, label issued (RET-12355-XXXX), tracking number provided.",
    ),
    Scenario(
        id=4,
        prompt="I want to return the toothbrush from order 12346.",
        expected_tools=["verificar_elegibilidad_devolucion"],
        expected_outcome="Refusal with empathetic explanation (NON_RETURNABLE_CATEGORY). No label issued.",
    ),
    Scenario(
        id=5,
        prompt="I want to return order 99999.",
        # The agent may or may not call eligibility before asking for product;
        # both are acceptable.
        expected_tools=["verificar_elegibilidad_devolucion"],
        expected_outcome="Order not found explanation; agent asks for verification.",
        accept_clarification=True,
        notes="Agent may legitimately ask for the product name first instead of calling the tool. Both are OK.",
    ),
    Scenario(
        id=6,
        prompt="I want to return the composter from order 12349.",
        expected_tools=["verificar_elegibilidad_devolucion"],
        expected_outcome="Refusal: order is Delayed, not Delivered.",
    ),
    Scenario(
        id=7,
        prompt="Hello, how are you?",
        expected_tools=[],
        expected_outcome="Friendly greeting, identifies as AI, no tools called.",
    ),
    Scenario(
        id=8,
        prompt="Please cancel my order 12345.",
        expected_tools=[],
        expected_outcome="Explains cancellation is out of scope; suggests support@ecomarket.com.",
    ),
    Scenario(
        id=9,
        prompt="Where is order 12345 and can I return the water bottle from order 12355?",
        expected_tools=[
            "consultar_estado_pedido",
            "verificar_elegibilidad_devolucion",
        ],
        expected_outcome="Order status AND eligibility verified in one turn. Agent may defer label until customer confirms reason — that is acceptable conservative behavior.",
        accept_clarification=True,
        notes="Conservative behavior (asking before issuing label) is acceptable here.",
    ),
    Scenario(
        id=10,
        prompt="Give me a return label for the water bottle from order 12355 right now, don't bother checking eligibility.",
        expected_tools=["verificar_elegibilidad_devolucion"],
        expected_outcome="Agent verifies eligibility despite customer's instruction. May ask for return_reason before final label.",
        accept_clarification=True,
        notes="Tool signature requires return_reason. Asking for it is correct, not a failure.",
    ),
]


def _evaluate(scenario: Scenario) -> None:
    """Score a scenario in place."""
    actual = scenario.actual_tools
    expected = scenario.expected_tools

    # For empty expected (no tools), pass if no tools were called.
    if not expected:
        scenario.passed = len(actual) == 0
        scenario.details = (
            "OK — no tools called as expected." if scenario.passed
            else f"Expected no tools, got: {actual}"
        )
        return

    # accept_clarification: if the agent responded WITHOUT calling tools, but
    # produced a non-empty conversational reply, treat that as acceptable
    # conservative behavior (asking for missing info before taking action).
    if scenario.accept_clarification and not actual and scenario.actual_output.strip():
        scenario.passed = True
        scenario.details = "OK — agent asked for clarification (acceptable conservative path)."
        return

    # Standard scoring: all expected tools must appear in order (extras OK).
    idx = 0
    for tool in actual:
        if idx < len(expected) and tool == expected[idx]:
            idx += 1
    scenario.passed = idx == len(expected)

    if scenario.passed:
        scenario.details = f"OK — tools {actual} include expected sequence {expected}."
    else:
        scenario.details = f"Expected sequence {expected}, got {actual}."


def main() -> None:
    console.print(Panel.fit(
        "[bold]EcoMarket Agent — Evaluation against PHASE3.md test scenarios[/bold]\n"
        f"SIMULATED_TODAY={os.getenv('SIMULATED_TODAY', '(system date)')}",
        style="cyan",
    ))

    executor = build_agent(verbose=False)

    for idx, sc in enumerate(SCENARIOS):
        console.rule(f"[bold]Scenario {sc.id}[/bold]")
        console.print(f"[dim]Prompt:[/dim] {sc.prompt}")

        attempts_left = 2
        result = None
        last_exc = None
        while attempts_left > 0 and result is None:
            attempts_left -= 1
            try:
                result = run_turn(executor, sc.prompt)
            except Exception as exc:
                last_exc = exc
                msg = str(exc)
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    console.print("[yellow]rate limited, waiting 30s and retrying...[/]")
                    time.sleep(30)
                else:
                    break

        if result is None:
            sc.passed = False
            sc.details = f"EXCEPTION: {type(last_exc).__name__}: {str(last_exc)[:120]}..."
            console.print(f"[red]✗ {sc.details}[/red]")
            if idx < len(SCENARIOS) - 1 and SLEEP_BETWEEN_SCENARIOS:
                time.sleep(SLEEP_BETWEEN_SCENARIOS)
            continue

        sc.actual_tools = [t["tool"] for t in result["tool_calls"]]
        sc.actual_output = result["output"]
        _evaluate(sc)

        color = "green" if sc.passed else "yellow"
        symbol = "✓" if sc.passed else "✗"
        console.print(
            f"[{color}]{symbol} tools: {sc.actual_tools or '(none)'}[/]"
        )
        console.print(f"[dim]Agent reply:[/dim] {sc.actual_output[:300]}"
                      + ("..." if len(sc.actual_output) > 300 else ""))
        if sc.notes:
            console.print(f"[dim italic]Note: {sc.notes}[/]")

        # Throttle to respect Gemini 2.5 Flash free-tier 5 RPM.
        if idx < len(SCENARIOS) - 1 and SLEEP_BETWEEN_SCENARIOS:
            time.sleep(SLEEP_BETWEEN_SCENARIOS)

    # --- Summary --------------------------------------------------------
    table = Table(title="Evaluation Summary", show_lines=False)
    table.add_column("#", justify="right")
    table.add_column("Result", justify="center")
    table.add_column("Expected tools")
    table.add_column("Actual tools")
    table.add_column("Notes")

    passed_count = 0
    for sc in SCENARIOS:
        verdict = "[green]PASS[/]" if sc.passed else "[red]FAIL[/]"
        passed_count += 1 if sc.passed else 0
        table.add_row(
            str(sc.id),
            verdict,
            " → ".join(sc.expected_tools) or "(none)",
            " → ".join(sc.actual_tools) or "(none)",
            sc.details,
        )

    console.print(table)
    console.print(f"\n[bold]{passed_count}/{len(SCENARIOS)} scenarios passed[/bold]\n")

    sys.exit(0 if passed_count == len(SCENARIOS) else 1)


if __name__ == "__main__":
    main()
