"""
LangSmith configuration helpers.

LangChain can trace runs automatically when the LangSmith environment variables
are present. This module keeps those defaults consistent across CLI scripts and
the future web app.
"""

import os
from typing import Dict

from dotenv import load_dotenv


DEFAULT_LANGSMITH_PROJECT = "ecomarket-final-agent"
TRUTHY_VALUES = {"1", "true", "yes", "on"}


def _is_truthy(value: str | None) -> bool:
    """Return whether an environment value should be treated as enabled."""
    return str(value or "").strip().lower() in TRUTHY_VALUES


def configure_langsmith() -> Dict[str, str | bool | None]:
    """
    Load LangSmith-related environment variables and set compatibility aliases.

    Returns:
        A small status dictionary useful for CLIs and UI diagnostics.
    """
    load_dotenv()

    tracing_enabled = _is_truthy(os.getenv("LANGSMITH_TRACING"))
    project_name = os.getenv("LANGSMITH_PROJECT") or DEFAULT_LANGSMITH_PROJECT

    if tracing_enabled:
        os.environ.setdefault("LANGSMITH_PROJECT", project_name)
        os.environ.setdefault("LANGCHAIN_PROJECT", project_name)
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")

    return {
        "enabled": tracing_enabled,
        "project": project_name,
        "api_key_configured": bool(os.getenv("LANGSMITH_API_KEY")),
    }
