"""Streamlit UI for the EcoMarket AI Agent — Phase 4 of the Final Project.

Run with:
    streamlit run streamlit_app.py

Features:
- Chat-style multi-turn interface (st.chat_message + st.chat_input).
- Model selector in the sidebar — switch between Gemini variants on the fly
  when one hits its daily free-tier quota.
- Suggested prompts grouped by intent (orders, policies, returns,
  out-of-scope) with one-click submission.
- Empty-state cards on first visit so users know what they can ask.
- Per-turn tool trace (collapsible JSON of inputs/outputs) — this is the
  operational view that backs the observability proposal in PHASE4.md.
- Highlighted card when the agent issues a return label.

Justification of Streamlit over Gradio (Phase 4 deliverable):
- Native chat primitives are more polished for multi-turn agents.
- Sidebar layout + custom CSS support the operational look-and-feel we need.
- `st.cache_resource` cleanly caches the agent build per model.
- Streamlit Cloud / HuggingFace Spaces / internal deploys without code changes.
"""
from __future__ import annotations

import json
import os
from datetime import date

import streamlit as st

# --- App config (must be first Streamlit call) -------------------------------
st.set_page_config(
    page_title="EcoMarket AI Assistant",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Imports that touch app/* go below set_page_config so any import error
# surfaces inside the Streamlit error UI rather than killing the process.
from app.agent import build_agent, run_turn  # noqa: E402
from app.config import GEMINI_MODEL, get_today  # noqa: E402
from app.logger import get_log_path  # noqa: E402


# --- Constants ---------------------------------------------------------------
MODEL_CHOICES = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]

SUGGESTED_PROMPTS: dict[str, list[tuple[str, str]]] = {
    "Order tracking": [
        ("Where is order 12345?", "Look up status of an in-transit order."),
        ("Where is order 12354?", "Look up a delivered order."),
    ],
    "Return policy": [
        ("Can I return a bamboo toothbrush?", "Generic policy lookup."),
        ("What's your return policy on water bottles?", "Returnable category."),
    ],
    "Start a return": [
        (
            "I want to return the water bottle from order 12355 because it leaks.",
            "Happy path — eligible, label issued.",
        ),
        (
            "I want to return the toothbrush from order 12346.",
            "Refused — non-returnable category.",
        ),
        (
            "I want to return the composter from order 12349.",
            "Refused — order not yet delivered.",
        ),
    ],
    "Out of scope": [
        ("Please cancel my order 12345.", "Agent should decline and escalate."),
    ],
}


# --- Custom CSS --------------------------------------------------------------
CUSTOM_CSS = """
<style>
/* Tighten main container */
.main .block-container {
    padding-top: 1.4rem;
    padding-bottom: 4rem;
    max-width: 1100px;
}

/* Hero header card */
.eco-hero {
    background: linear-gradient(135deg,
        rgba(78, 145, 96, 0.18) 0%,
        rgba(78, 145, 96, 0.04) 100%);
    border-left: 4px solid #4e9160;
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}
.eco-hero h1 {
    margin: 0;
    font-size: 1.7rem;
    font-weight: 600;
    letter-spacing: -0.01em;
}
.eco-hero p {
    margin: 0.35rem 0 0 0;
    opacity: 0.78;
    font-size: 0.95rem;
}

/* Status chips row */
.eco-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    margin: 0.75rem 0 1rem 0;
}
.eco-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.25rem 0.7rem;
    background: rgba(128, 128, 128, 0.16);
    border: 1px solid rgba(128, 128, 128, 0.22);
    border-radius: 999px;
    font-size: 0.78rem;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.eco-chip-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #4caf50;
    box-shadow: 0 0 6px rgba(76, 175, 80, 0.6);
}

/* Empty-state grid of starter prompts */
.eco-empty-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 0.6rem;
    margin: 0.75rem 0 1rem 0;
}
.eco-card-section-title {
    font-size: 0.74rem;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    opacity: 0.55;
    margin: 1rem 0 0.4rem 0;
    font-weight: 600;
}

/* Sidebar polish */
section[data-testid="stSidebar"] h3 {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    opacity: 0.6;
    margin-top: 1.1rem;
    margin-bottom: 0.4rem;
    font-weight: 700;
}
section[data-testid="stSidebar"] .stButton button {
    text-align: left;
    justify-content: flex-start;
    font-size: 0.83rem;
    padding: 0.38rem 0.7rem;
    line-height: 1.25;
    white-space: normal;
    height: auto;
    min-height: 2rem;
    border: 1px solid rgba(128, 128, 128, 0.18);
}
section[data-testid="stSidebar"] .stButton button:hover {
    border-color: #4e9160;
    color: #4e9160;
}

/* Chat message tweaks */
[data-testid="stChatMessage"] {
    padding: 0.5rem 0.25rem;
}

/* Tool-trace expander */
[data-testid="stExpander"] summary {
    font-size: 0.82rem;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    opacity: 0.85;
}

/* Footer disclaimer */
.eco-footer {
    margin-top: 1.5rem;
    font-size: 0.72rem;
    opacity: 0.5;
    text-align: center;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# --- Agent cache (re-builds when model changes) ------------------------------
@st.cache_resource(show_spinner="Loading agent…")
def _get_agent(model_name: str):
    return build_agent(model=model_name)


# --- Helpers -----------------------------------------------------------------
def _parse_tool_output(raw):
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"_raw": raw}
    return {"_raw": str(raw)}


def _extract_issued_label(tool_calls: list[dict]) -> dict | None:
    for tc in reversed(tool_calls):
        if tc.get("tool") != "generar_etiqueta_devolucion":
            continue
        out = _parse_tool_output(tc.get("outputs"))
        if out.get("success"):
            return out
    return None


def _render_tool_calls(tool_calls: list[dict]) -> None:
    if not tool_calls:
        st.caption("No tools called — direct response.")
        return
    names = " → ".join(tc.get("tool", "?") for tc in tool_calls)
    label = f"Tool trace ({len(tool_calls)} call{'s' if len(tool_calls) != 1 else ''}): {names}"
    with st.expander(label, expanded=False):
        for i, tc in enumerate(tool_calls, start=1):
            st.markdown(f"**{i}. `{tc.get('tool', '?')}`**")
            c1, c2 = st.columns(2)
            with c1:
                st.caption("Inputs")
                st.json(tc.get("inputs", {}))
            with c2:
                st.caption("Outputs")
                st.json(_parse_tool_output(tc.get("outputs")))


def _render_label_card(label: dict) -> None:
    expires_at = str(label.get("expires_at", ""))
    expires_short = expires_at.split("T")[0] if "T" in expires_at else expires_at
    instr = label.get("instructions", []) or []

    st.success("Return label issued", icon=None)
    c1, c2, c3 = st.columns(3)
    c1.metric("Label ID", label.get("label_id", "-"))
    c2.metric("Tracking", label.get("tracking_number", "-"))
    c3.metric("Expires", expires_short or "-")
    st.caption(
        f"Carrier: **{label.get('carrier', '-')}**"
        f"  ·  Order: **{label.get('order_id', '-')}**"
        f"  ·  Product: **{label.get('product_name', '-')}**"
    )
    if instr:
        st.markdown("**Next steps**")
        for i, step in enumerate(instr, start=1):
            st.markdown(f"&nbsp;&nbsp;{i}. {step}", unsafe_allow_html=True)


def _submit_prompt(text: str) -> None:
    """Queue a prompt to be processed on next rerun (used by example buttons)."""
    st.session_state["pending_input"] = text
    st.rerun()


# --- Session state -----------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "selected_model" not in st.session_state:
    st.session_state["selected_model"] = GEMINI_MODEL


# --- Sidebar -----------------------------------------------------------------
with st.sidebar:
    st.markdown("### EcoMarket")
    st.markdown(
        "<div style='margin-top:-0.6rem;opacity:0.7;font-size:0.85rem;'>"
        "AI customer service agent</div>",
        unsafe_allow_html=True,
    )

    st.markdown("### Model")
    chosen_model = st.selectbox(
        "Model",
        options=MODEL_CHOICES,
        index=MODEL_CHOICES.index(st.session_state["selected_model"])
            if st.session_state["selected_model"] in MODEL_CHOICES
            else 0,
        label_visibility="collapsed",
        help=(
            "Free-tier daily quotas differ per model. If one is rate-limited, "
            "switch to another."
        ),
    )
    if chosen_model != st.session_state["selected_model"]:
        st.session_state["selected_model"] = chosen_model

    st.markdown("### Environment")
    today = get_today()
    sim_override = bool(os.getenv("SIMULATED_TODAY"))
    st.markdown(
        f"- **Date:** `{today.isoformat()}`"
        + (" *(simulated)*" if sim_override else " *(system)*")
    )
    log_path = get_log_path()
    try:
        rel = log_path.relative_to(log_path.parents[1])
    except ValueError:
        rel = log_path.name
    st.markdown(f"- **Tool log:** `{rel}`")

    st.markdown("### Try asking")
    for section, items in SUGGESTED_PROMPTS.items():
        st.markdown(
            f"<div style='font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;opacity:0.55;margin:0.6rem 0 0.25rem 0;'>{section}</div>",
            unsafe_allow_html=True,
        )
        for prompt_text, _hint in items:
            if st.button(prompt_text, key=f"side_{hash(prompt_text)}", use_container_width=True):
                _submit_prompt(prompt_text)

    st.markdown("### Conversation")
    if st.button("Clear conversation", use_container_width=True, key="clear_chat"):
        st.session_state["messages"] = []
        st.rerun()

    transcript = "\n\n".join(
        f"**{m['role'].upper()}**: {m['content']}"
        for m in st.session_state["messages"]
    )
    st.download_button(
        "Download transcript",
        data=transcript or "(empty)",
        file_name="ecomarket_chat.md",
        mime="text/markdown",
        use_container_width=True,
        disabled=not st.session_state["messages"],
    )

    st.markdown(
        "<div class='eco-footer'>"
        "AI assistant. For complex situations, contact support@ecomarket.com."
        "</div>",
        unsafe_allow_html=True,
    )


# --- Hero header + status chips ---------------------------------------------
st.markdown(
    """
<div class='eco-hero'>
  <h1>EcoMarket AI Assistant</h1>
  <p>Order tracking, return policies, and automated return-label generation.</p>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    f"""
<div class='eco-chips'>
  <span class='eco-chip'><span class='eco-chip-dot'></span>Online</span>
  <span class='eco-chip'>model: {chosen_model}</span>
  <span class='eco-chip'>today: {today.isoformat()}{' (sim)' if sim_override else ''}</span>
  <span class='eco-chip'>4 tools</span>
</div>
""",
    unsafe_allow_html=True,
)


# --- Empty state -------------------------------------------------------------
if not st.session_state["messages"]:
    st.markdown(
        "<div class='eco-card-section-title'>Start with an example</div>",
        unsafe_allow_html=True,
    )
    # Render the first item from each category as a clickable card.
    cols = st.columns(len(SUGGESTED_PROMPTS))
    for col, (section, items) in zip(cols, SUGGESTED_PROMPTS.items()):
        with col:
            prompt_text, hint = items[0]
            st.markdown(f"**{section}**")
            st.caption(hint)
            if st.button(
                prompt_text,
                key=f"empty_{hash(section)}",
                use_container_width=True,
            ):
                _submit_prompt(prompt_text)


# --- Render conversation -----------------------------------------------------
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("tool_calls"):
            label = _extract_issued_label(msg["tool_calls"])
            if label:
                _render_label_card(label)
            _render_tool_calls(msg["tool_calls"])


# --- Input + agent call ------------------------------------------------------
pending = st.session_state.pop("pending_input", None)
user_input = pending or st.chat_input(
    "Ask about an order, policy, or start a return…"
)

if user_input:
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state["messages"][:-1]
    ]

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                agent = _get_agent(chosen_model)
                result = run_turn(agent, user_input, history=history)
            except RuntimeError as exc:
                st.error(str(exc))
                st.session_state["messages"].pop()
                st.stop()
            except Exception as exc:
                msg = str(exc)
                if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
                    st.warning(
                        "Gemini's free-tier quota was hit for "
                        f"**`{chosen_model}`**. Try a different model from the "
                        "sidebar — each has its own daily allowance. "
                        "(`gemini-2.0-flash` usually has the most headroom.)"
                    )
                else:
                    st.error(f"Agent error: `{type(exc).__name__}`: {exc}")
                st.session_state["messages"].pop()
                st.stop()

        st.markdown(result["output"] or "_(no response)_")

        issued = _extract_issued_label(result["tool_calls"])
        if issued:
            _render_label_card(issued)

        _render_tool_calls(result["tool_calls"])

    st.session_state["messages"].append(
        {
            "role": "assistant",
            "content": result["output"] or "_(no response)_",
            "tool_calls": result["tool_calls"],
        }
    )
