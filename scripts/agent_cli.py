"""Interactive REPL for the EcoMarket agent.

Useful for hand-testing before/instead of the Streamlit UI. Maintains
conversation history across turns so you can validate multi-turn flows like:
    > I want to return something from order 12355.
    > the water bottle, because it leaks.

Usage:
    python -m scripts.agent_cli
    # Optional:
    SIMULATED_TODAY=2026-05-15 python -m scripts.agent_cli
"""
from __future__ import annotations

import os
import sys

from rich.console import Console
from rich.panel import Panel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent import build_agent, run_turn  # noqa: E402
from app.logger import get_log_path  # noqa: E402

console = Console()


def main() -> None:
    console.print(Panel.fit(
        "[bold green]🌿 EcoMarket Agent — interactive CLI[/]\n"
        "Type your question. Empty line or 'quit' to exit.\n"
        f"Tool calls are logged to: [dim]{get_log_path()}[/]",
        style="green",
    ))

    executor = build_agent(verbose=False)
    history: list[dict] = []

    while True:
        try:
            user_input = console.input("\n[bold cyan]You:[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]bye[/]")
            return
        if not user_input or user_input.lower() in {"quit", "exit"}:
            console.print("[dim]bye[/]")
            return

        try:
            result = run_turn(executor, user_input, history=history)
        except Exception as exc:
            console.print(f"[red]Error:[/] {type(exc).__name__}: {exc}")
            continue

        if result["tool_calls"]:
            tools_used = ", ".join(t["tool"] for t in result["tool_calls"])
            console.print(f"[dim italic]→ tools: {tools_used}[/]")
        console.print(f"[bold magenta]Agent:[/] {result['output']}")

        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": result["output"]})


if __name__ == "__main__":
    main()
