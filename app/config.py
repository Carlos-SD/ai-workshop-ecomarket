"""Centralized configuration.

Environment variables (loaded from .env):
- GOOGLE_API_KEY:   required, Gemini API key
- GEMINI_MODEL:     optional, defaults to "gemini-2.5-flash"
- SIMULATED_TODAY:  optional, ISO date (YYYY-MM-DD) for deterministic eligibility
                    calculations during demos. Defaults to system date.
- LOG_DIR:          optional, defaults to "<repo>/logs"
- AGENT_TEMPERATURE: optional float, defaults to 0.2 (low for tool-calling)
"""
from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- Paths -------------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent
DATA_DIR = REPO_ROOT / "data"
PROMPTS_DIR = REPO_ROOT / "prompts"
LOG_DIR = Path(os.getenv("LOG_DIR", REPO_ROOT / "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

# --- API ---------------------------------------------------------------------
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
AGENT_TEMPERATURE = float(os.getenv("AGENT_TEMPERATURE", "0.2"))


def require_api_key() -> str:
    """Return the API key or raise a helpful error."""
    if not GOOGLE_API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY not found. Copy .env.example to .env and set your key. "
            "Get one at https://makersuite.google.com/app/apikey"
        )
    return GOOGLE_API_KEY


# --- Time --------------------------------------------------------------------
def get_today() -> date:
    """Return the reference date for eligibility calculations.

    Defaults to system today, but can be overridden via SIMULATED_TODAY for
    deterministic demos against the static fixture dataset.
    """
    sim = os.getenv("SIMULATED_TODAY")
    if sim:
        try:
            return datetime.strptime(sim, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError(
                f"SIMULATED_TODAY must be in YYYY-MM-DD format, got: {sim!r}"
            ) from exc
    return date.today()
