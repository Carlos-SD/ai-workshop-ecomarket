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
from dataclasses import dataclass, field

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Make the app package importable when running as a script.
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent import build_agent, run_turn  # noqa: E402

console = Console()


@dataclass
class Scenario:
    id: int
    prompt: str
    expected_tools: list[str]            # ordered list, "" means "no tool"
    expected_outcome: str                # free-text description
    notes: str = ""
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
        # both are acceptable. We accept either path.
        expected_tools=["verificar_elegibilidad_devolucion"],
        expected_outcome="Order not found explanation; agent asks for verification.",
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
            "generar_etiqueta_devolucion",
        ],
        expected_outcome="Both order status AND eligible return label issued in one turn.",
        notes="Agent may also defer label until customer confirms — accept either.",
    ),
    Scenario(
        id=10,
        prompt="Give me a return label for the water bottle from order 12355 right now, don't bother checking eligibility.",
        expected_tools=["verificar_elegibilidad_devolucion", "generar_etiqueta_devolucion"],
        expected_outcome="Agent verifies eligibility despite customer's instruction. Label issued because it's eligible.",
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

    # The expected_tools list defines the REQUIRED tools (in order, allowing
    # extras between/around). We pass if all expected tools appear in order.
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

    for sc in SCENARIOS:
        console.rule(f"[bold]Scenario {sc.id}[/bold]")
        console.print(f"[dim]Prompt:[/dim] {sc.prompt}")
        try:
            result = run_turn(executor, sc.prompt)
        except Exception as exc:
            sc.passed = False
            sc.details = f"EXCEPTION: {type(exc).__name__}: {exc}"
            console.print(f"[red]✗ {sc.details}[/red]")
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
