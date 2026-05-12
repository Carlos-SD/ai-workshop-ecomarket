"""
LangChain return agent for EcoMarket.

The agent uses Gemini to orchestrate deterministic return workflow tools. The
model can decide which tool to call, but business decisions remain inside the
tools implemented in return_tools.py.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

from return_tools import (
    consultar_pedido,
    generar_etiqueta_devolucion,
    registrar_solicitud_devolucion,
    verificar_elegibilidad_devolucion,
)


PROJECT_ROOT = Path(__file__).parent.parent
PROMPT_PATH = PROJECT_ROOT / "prompts" / "return_agent_prompt.txt"
DEFAULT_MODEL = "gemini-2.5-flash"


def load_environment() -> str:
    """Load environment variables and validate the Gemini API key."""
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not found in .env file")

    return api_key


def load_agent_prompt() -> str:
    """Load the return-agent system prompt from disk."""
    with open(PROMPT_PATH, "r", encoding="utf-8") as file:
        return file.read()


def extract_return_fields(text: str) -> Dict[str, str]:
    """
    Extract common return fields from a customer message.

    This helper is intentionally conservative. The agent can still ask for
    missing data when these fields are not found.
    """
    order_match = re.search(r"\b(\d{5,})\b", text)
    order_id = order_match.group(1) if order_match else ""

    product = text
    if order_id:
        product = product.replace(order_id, " ")

    cleanup_patterns = [
        r"\bquiero\b",
        r"\bdevolver\b",
        r"\bdevolucion\b",
        r"\bdevolución\b",
        r"\bretornar\b",
        r"\bregresar\b",
        r"\bproducto\b",
        r"\bpedido\b",
        r"\borden\b",
        r"\bdel\b",
        r"\bde la\b",
        r"\bde el\b",
        r"\bmi\b",
        r"\bpor favor\b",
    ]
    for pattern in cleanup_patterns:
        product = re.sub(pattern, " ", product, flags=re.IGNORECASE)

    product = re.sub(r"[^A-Za-zÁÉÍÓÚáéíóúÑñ0-9 ]+", " ", product)
    product = re.sub(r"\s+", " ", product).strip()

    return {
        "order_id": order_id,
        "product_name": product,
    }


@tool
def consultar_pedido_tool(order_id: str) -> Dict[str, Any]:
    """Look up an EcoMarket order by order ID."""
    return consultar_pedido(order_id)


@tool
def verificar_elegibilidad_devolucion_tool(order_id: str, product_name: str) -> Dict[str, Any]:
    """Verify whether a product in an order is eligible for return."""
    return verificar_elegibilidad_devolucion(order_id, product_name)


@tool
def generar_etiqueta_devolucion_tool(order_id: str, product_name: str) -> Dict[str, Any]:
    """Generate a simulated return label for an eligible product return."""
    return generar_etiqueta_devolucion(order_id, product_name)


@tool
def registrar_solicitud_devolucion_tool(
    order_id: str,
    product_name: str,
    status: str,
    return_id: str = "",
    error_code: str = "",
) -> Dict[str, Any]:
    """Register a local audit record for a return request."""
    result = {
        "ok": status.lower() in {"approved", "aprobada", "success", "ok"},
        "status": status,
        "return_id": return_id or None,
        "error_code": error_code or None,
    }

    return registrar_solicitud_devolucion(order_id, product_name, result)


RETURN_AGENT_TOOLS = [
    consultar_pedido_tool,
    verificar_elegibilidad_devolucion_tool,
    generar_etiqueta_devolucion_tool,
    registrar_solicitud_devolucion_tool,
]


def build_return_agent(model_name: str = DEFAULT_MODEL):
    """Build the LangChain agent graph for the return workflow."""
    load_environment()
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0.2,
        max_tokens=800,
    )
    return create_agent(
        model=llm,
        tools=RETURN_AGENT_TOOLS,
        system_prompt=load_agent_prompt(),
        name="ecomarket_return_agent",
    )


def _message_to_dict(message: BaseMessage) -> Dict[str, Any]:
    """Convert a LangChain message into a compact serializable structure."""
    payload = {
        "type": message.type,
        "content": _content_to_text(message.content),
    }

    if isinstance(message, AIMessage) and getattr(message, "tool_calls", None):
        payload["tool_calls"] = message.tool_calls

    if isinstance(message, ToolMessage):
        payload["tool_name"] = message.name
        payload["tool_call_id"] = message.tool_call_id

    return payload


def _content_to_text(content: Any) -> str:
    """Convert provider-specific message content into plain text."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and "text" in item:
                    parts.append(str(item["text"]))
                elif "content" in item:
                    parts.append(str(item["content"]))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)

    return str(content)


def _extract_tool_trace(messages: List[BaseMessage]) -> List[Dict[str, Any]]:
    """Extract tool call and tool response metadata from agent messages."""
    trace = []

    for message in messages:
        if isinstance(message, AIMessage) and getattr(message, "tool_calls", None):
            for call in message.tool_calls:
                trace.append({
                    "event": "tool_call",
                    "name": call.get("name"),
                    "args": call.get("args"),
                    "id": call.get("id"),
                })

        if isinstance(message, ToolMessage):
            trace.append({
                "event": "tool_result",
                "name": message.name,
                "tool_call_id": message.tool_call_id,
                "content": message.content,
            })

    return trace


def run_return_agent(message: str, model_name: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """
    Run the return agent for a single customer message.

    Args:
        message: Customer request in Spanish.
        model_name: Gemini model name accepted by ChatGoogleGenerativeAI.

    Returns:
        A dictionary with the final answer and execution metadata.
    """
    agent = build_return_agent(model_name=model_name)
    extracted = extract_return_fields(message)
    enriched_message = (
        f"Mensaje del cliente: {message}\n\n"
        f"Datos detectados automaticamente:\n"
        f"- order_id: {extracted['order_id'] or 'NO_DETECTADO'}\n"
        f"- product_name: {extracted['product_name'] or 'NO_DETECTADO'}\n\n"
        "Usa los datos detectados solo si son correctos para la solicitud."
    )

    result = agent.invoke({"messages": [HumanMessage(content=enriched_message)]})
    messages = result.get("messages", [])
    final_message = _content_to_text(messages[-1].content) if messages else ""

    return {
        "route": "return_agent",
        "answer": final_message,
        "extracted_fields": extracted,
        "tool_trace": _extract_tool_trace(messages),
        "messages": [_message_to_dict(message_item) for message_item in messages],
    }


def _run_cli() -> None:
    """Run an interactive or one-shot CLI for the return agent."""
    parser = argparse.ArgumentParser(description="EcoMarket return agent")
    parser.add_argument("--message", help="Customer message to process")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full structured result as JSON",
    )
    args = parser.parse_args()

    try:
        if args.message:
            result = run_return_agent(args.message, model_name=args.model)
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(result["answer"])
            return

        print("ECOMARKET - RETURN AGENT")
        print("Type 'salir' to exit.")
        while True:
            customer_message = input("\nCliente: ").strip()
            if customer_message.lower() in {"salir", "exit", "quit"}:
                break
            if not customer_message:
                continue
            result = run_return_agent(customer_message, model_name=args.model)
            print(f"\nAgente: {result['answer']}")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _run_cli()
