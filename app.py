"""
Streamlit interface for the EcoMarket customer-service assistant.

The app sends each customer message through the router so informational
questions use RAG and actionable return requests use the return agent.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st


PROJECT_ROOT = Path(__file__).parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from customer_service_router import handle_customer_message  # noqa: E402
from langsmith_config import configure_langsmith  # noqa: E402


st.set_page_config(
    page_title="EcoMarket Assistant",
    page_icon=None,
    layout="wide",
)


def _tool_names(tool_trace: List[Dict[str, Any]]) -> List[str]:
    """Return the ordered list of tool-call names from a trace."""
    return [
        event.get("name", "")
        for event in tool_trace
        if event.get("event") == "tool_call"
    ]


def _render_result_details(result: Dict[str, Any]) -> None:
    """Render route, tools, and trace details for debugging and demos."""
    classification = result.get("classification", {})
    route = result.get("route", classification.get("route", "unknown"))
    tool_names = _tool_names(result.get("tool_trace", []))
    langsmith = result.get("langsmith", configure_langsmith())

    cols = st.columns(3)
    cols[0].metric("Ruta", route)
    cols[1].metric("Tools", len(tool_names))
    cols[2].metric("LangSmith", "Activo" if langsmith.get("enabled") else "Inactivo")

    if result.get("error"):
        st.warning(f"Error controlado: {result.get('error_type', 'runtime_error')}")

    if tool_names:
        st.write("Tools llamadas:")
        st.code("\n".join(tool_names), language="text")

    with st.expander("Detalle tecnico"):
        st.json({
            "classification": classification,
            "langsmith": langsmith,
            "tool_trace": result.get("tool_trace", []),
            "fallback_used": result.get("fallback_used"),
            "best_score": result.get("best_score"),
            "error": result.get("error"),
            "error_type": result.get("error_type"),
            "technical_detail": result.get("technical_detail"),
        })


def _initialize_state() -> None:
    """Initialize Streamlit session state."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_result" not in st.session_state:
        st.session_state.last_result = None


def _handle_prompt(prompt: str) -> None:
    """Process one user prompt through the customer-service router."""
    st.session_state.messages.append({"role": "user", "content": prompt})

    try:
        with st.spinner("Procesando..."):
            result = handle_customer_message(prompt)
    except Exception as exc:
        result = {
            "route": "error",
            "answer": (
                "No pude procesar la solicitud en este momento. "
                f"Detalle tecnico: {exc}"
            ),
            "classification": {},
            "tool_trace": [],
            "langsmith": configure_langsmith(),
        }

    st.session_state.last_result = result
    st.session_state.messages.append({
        "role": "assistant",
        "content": result.get("answer", ""),
    })


def main() -> None:
    """Render the Streamlit app."""
    _initialize_state()

    st.title("EcoMarket")
    st.caption("Asistente de servicio al cliente")

    with st.sidebar:
        st.subheader("Estado")
        langsmith = configure_langsmith()
        st.write(f"LangSmith: {'activo' if langsmith.get('enabled') else 'inactivo'}")
        st.write(f"Proyecto: {langsmith.get('project')}")
        st.divider()

        if st.button("Limpiar conversacion", use_container_width=True):
            st.session_state.messages = []
            st.session_state.last_result = None
            st.rerun()

        st.subheader("Ejemplos")
        examples = [
            "Quiero devolver la botella de bambu del pedido 12345",
            "Quiero devolver el champu solido del pedido 12347",
            "Cuanto cuesta el envio a Medellin?",
        ]
        for example in examples:
            if st.button(example, use_container_width=True):
                _handle_prompt(example)
                st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Mensaje del cliente")
    if prompt:
        _handle_prompt(prompt)
        st.rerun()

    if st.session_state.last_result:
        _render_result_details(st.session_state.last_result)


if __name__ == "__main__":
    main()
