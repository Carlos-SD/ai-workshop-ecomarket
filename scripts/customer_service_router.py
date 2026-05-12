"""
Router for EcoMarket customer-service requests.

The router keeps information retrieval and action-taking separate:
- Informational questions go to the existing RAG system.
- Actionable return requests go to the LangChain return agent.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

from langchain_google_genai import ChatGoogleGenerativeAI

from langsmith_config import configure_langsmith
from rag_query import (
    load_environment as load_rag_environment,
    load_prompt_template,
    load_vectorstore,
    query_rag,
)
from return_agent import DEFAULT_MODEL, run_return_agent


RETURN_TERMS = [
    "devolucion",
    "devolución",
    "devolver",
    "devuelvo",
    "retornar",
    "retorno",
    "regresar",
    "reembolso",
    "etiqueta",
]

ACTION_TERMS = [
    "quiero",
    "necesito",
    "ayudame",
    "ayúdame",
    "hacer",
    "iniciar",
    "procesar",
    "generar",
    "crear",
    "solicitar",
    "tramitar",
]

INFORMATION_TERMS = [
    "puedo",
    "cual",
    "cuál",
    "cuanto",
    "cuánto",
    "como",
    "cómo",
    "politica",
    "política",
    "plazo",
    "condiciones",
]


def _normalize_text(value: str) -> str:
    """Normalize text for lightweight intent classification."""
    return value.lower().strip()


def _contains_any(text: str, terms: List[str]) -> bool:
    """Return whether any configured term appears in the text."""
    return any(term in text for term in terms)


def classify_customer_intent(message: str) -> Dict[str, Any]:
    """
    Classify whether a message should use RAG or the return agent.

    The classifier is intentionally rule-based for transparency. It routes only
    actionable return workflows to the agent; informational return-policy
    questions can still be answered by RAG.
    """
    normalized = _normalize_text(message)
    has_order_id = bool(re.search(r"\b\d{5,}\b", normalized))
    has_return_term = _contains_any(normalized, RETURN_TERMS)
    has_action_term = _contains_any(normalized, ACTION_TERMS)
    has_information_term = _contains_any(normalized, INFORMATION_TERMS)

    if has_return_term and has_action_term:
        return {
            "route": "return_agent",
            "confidence": 0.9,
            "reason": "Detected an actionable return request.",
            "signals": {
                "has_order_id": has_order_id,
                "has_return_term": has_return_term,
                "has_action_term": has_action_term,
                "has_information_term": has_information_term,
            },
        }

    if has_return_term and has_order_id and not has_information_term:
        return {
            "route": "return_agent",
            "confidence": 0.8,
            "reason": "Detected a return request tied to an order.",
            "signals": {
                "has_order_id": has_order_id,
                "has_return_term": has_return_term,
                "has_action_term": has_action_term,
                "has_information_term": has_information_term,
            },
        }

    return {
        "route": "rag",
        "confidence": 0.75,
        "reason": "No actionable return workflow detected.",
        "signals": {
            "has_order_id": has_order_id,
            "has_return_term": has_return_term,
            "has_action_term": has_action_term,
            "has_information_term": has_information_term,
        },
    }


def _run_rag_route(message: str, model_name: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """Run the existing RAG system and return serializable metadata."""
    configure_langsmith()
    load_rag_environment()
    vectorstore = load_vectorstore()
    prompt_template = load_prompt_template()
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0.3,
        max_output_tokens=600,
        thinking_budget=0,
    )

    result = query_rag(
        question=message,
        vectorstore=vectorstore,
        llm=llm,
        prompt_template=prompt_template,
        verbose=False,
    )

    return {
        "route": "rag",
        "answer": result["answer"],
        "fallback_used": result["fallback_used"],
        "best_score": result["best_score"],
        "retrieved_documents": [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
            }
            for doc in result["retrieved_documents"]
        ],
    }


def handle_customer_message(message: str, model_name: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """
    Route a customer message to RAG or the return agent.

    Args:
        message: Customer message in Spanish.
        model_name: Gemini model name accepted by the LangChain model wrapper.

    Returns:
        A dictionary containing the selected route, answer, and route metadata.
    """
    langsmith_status = configure_langsmith()
    classification = classify_customer_intent(message)

    if classification["route"] == "return_agent":
        result = run_return_agent(message, model_name=model_name)
    else:
        result = _run_rag_route(message, model_name=model_name)

    result["classification"] = classification
    result["langsmith"] = langsmith_status
    return result


def _run_cli() -> None:
    """Run a command-line interface for the customer-service router."""
    parser = argparse.ArgumentParser(description="EcoMarket customer-service router")
    parser.add_argument("--message", help="Customer message to process")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full structured result as JSON",
    )
    parser.add_argument(
        "--classify-only",
        action="store_true",
        help="Only classify the route without calling RAG or the return agent",
    )
    args = parser.parse_args()

    if not args.message:
        print("ERROR: --message is required", file=sys.stderr)
        sys.exit(1)

    if args.classify_only:
        result = classify_customer_intent(args.message)
    else:
        result = handle_customer_message(args.message, model_name=args.model)

    if args.json or args.classify_only:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["answer"])


if __name__ == "__main__":
    _run_cli()
