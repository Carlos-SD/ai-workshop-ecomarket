"""LangChain agent factory.

Built on LangChain 1.x's `create_agent`, which returns a compiled LangGraph
under the hood. Same surface, more modern internals than the legacy
AgentExecutor.

Public API:
    build_agent()                                       -> CompiledStateGraph
    run_turn(agent, user_input, history=None)           -> dict

`run_turn` returns:
    output:        the agent's final reply string
    tool_calls:    list of {tool, inputs, outputs} dicts
    request_id:    correlation ID (also recorded in logs/tool_calls.jsonl)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_google_genai import ChatGoogleGenerativeAI

from .config import AGENT_TEMPERATURE, GEMINI_MODEL, PROMPTS_DIR, require_api_key
from .logger import new_request_id
from .tools import ALL_TOOLS


def _load_system_prompt() -> str:
    path: Path = PROMPTS_DIR / "agent_system_prompt.txt"
    return path.read_text(encoding="utf-8")


def build_agent(*, verbose: bool = False):
    """Construct the agent (compiled LangGraph) with all tools wired up.

    `verbose` toggles LangGraph's debug mode (prints state transitions).
    """
    api_key = require_api_key()

    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        temperature=AGENT_TEMPERATURE,
        google_api_key=api_key,
    )

    system_prompt = _load_system_prompt()
    return create_agent(
        model=llm,
        tools=ALL_TOOLS,
        system_prompt=system_prompt,
        debug=verbose,
    )


def _serialize_history(history: list[dict] | None) -> list[BaseMessage]:
    """Convert [{role, content}, ...] to LangChain messages."""
    if not history:
        return []
    out: list[BaseMessage] = []
    for h in history:
        role = h.get("role")
        content = h.get("content", "")
        if role == "user":
            out.append(HumanMessage(content=content))
        elif role == "assistant":
            out.append(AIMessage(content=content))
        elif role == "system":
            out.append(SystemMessage(content=content))
    return out


def _extract_tool_calls(new_messages: list[BaseMessage]) -> list[dict]:
    """Walk the new messages and pair tool invocations with their outputs."""
    calls: dict[str, dict] = {}
    order: list[str] = []
    for msg in new_messages:
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                tc_id = tc.get("id") or tc.get("name", "?")
                calls[tc_id] = {
                    "tool": tc.get("name", "?"),
                    "inputs": tc.get("args", {}),
                    "outputs": None,
                }
                order.append(tc_id)
        elif isinstance(msg, ToolMessage):
            tc_id = getattr(msg, "tool_call_id", None)
            if tc_id and tc_id in calls:
                calls[tc_id]["outputs"] = msg.content
    return [calls[i] for i in order]


def _final_text(new_messages: list[BaseMessage]) -> str:
    for msg in reversed(new_messages):
        if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
            content = msg.content
            if isinstance(content, str):
                return content
            # Gemini sometimes returns content as a list of parts.
            if isinstance(content, list):
                return "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
    return ""


def run_turn(agent, user_input: str, history: list[dict] | None = None) -> dict[str, Any]:
    """Execute one user turn and return a structured response."""
    request_id = new_request_id()
    incoming = _serialize_history(history)
    incoming.append(HumanMessage(content=user_input))

    result = agent.invoke({"messages": incoming})
    all_messages: list[BaseMessage] = result.get("messages", [])

    # Messages new to this turn = everything past the inputs we passed in.
    new_messages = all_messages[len(incoming) - 1 :]  # include the human msg we just sent

    return {
        "output": _final_text(new_messages),
        "tool_calls": _extract_tool_calls(new_messages),
        "request_id": request_id,
    }


__all__ = ["build_agent", "run_turn"]
