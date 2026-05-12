"""
Deterministic tools for EcoMarket return workflows.

These functions contain the business rules used by the return agent. They are
kept independent from the LLM so return approvals and labels are based on local
data, not on model guesses.
"""

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
ORDERS_PATH = DATA_DIR / "orders.json"
RETURN_POLICIES_PATH = DATA_DIR / "return_policies.json"
RETURN_REQUESTS_PATH = LOGS_DIR / "return_requests.json"


def _load_json(path: Path) -> Any:
    """Load a JSON file using UTF-8 encoding."""
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def _normalize_text(value: str) -> str:
    """Normalize user and catalog text for accent-insensitive matching."""
    normalized = unicodedata.normalize("NFD", value.lower())
    without_accents = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"[^a-z0-9]+", " ", without_accents).strip()


def _tokens(value: str) -> set:
    """Return normalized tokens while dropping very short words."""
    return {token for token in _normalize_text(value).split() if len(token) > 2}


def _match_score(query: str, candidate: str) -> float:
    """Compute a simple score for partial product-name matching."""
    query_norm = _normalize_text(query)
    candidate_norm = _normalize_text(candidate)

    if not query_norm or not candidate_norm:
        return 0.0

    if query_norm == candidate_norm:
        return 1.0

    if query_norm in candidate_norm or candidate_norm in query_norm:
        shorter = min(len(query_norm), len(candidate_norm))
        longer = max(len(query_norm), len(candidate_norm))
        return 0.85 + (0.15 * shorter / longer)

    query_tokens = _tokens(query)
    candidate_tokens = _tokens(candidate)

    if not query_tokens or not candidate_tokens:
        return 0.0

    overlap = len(query_tokens & candidate_tokens)
    return overlap / len(query_tokens | candidate_tokens)


def _find_best_match(query: str, candidates: List[str], min_score: float = 0.34) -> Optional[str]:
    """Find the closest candidate for a user-provided product name."""
    scored = [
        (_match_score(query, candidate), candidate)
        for candidate in candidates
    ]
    scored.sort(reverse=True, key=lambda item: item[0])

    if not scored or scored[0][0] < min_score:
        return None

    return scored[0][1]


def _load_orders() -> Dict[str, Dict[str, Any]]:
    """Load the local order database."""
    return _load_json(ORDERS_PATH)


def _load_return_policies() -> List[Dict[str, Any]]:
    """Load return policies as a list of product policy records."""
    return _load_json(RETURN_POLICIES_PATH)["return_policies"]


def consultar_pedido(order_id: str) -> Dict[str, Any]:
    """
    Look up an order by ID.

    Args:
        order_id: EcoMarket order identifier.

    Returns:
        A JSON-friendly dictionary with order lookup status and data.
    """
    orders = _load_orders()
    order = orders.get(str(order_id).strip())

    if not order:
        return {
            "ok": False,
            "error_code": "ORDER_NOT_FOUND",
            "message": "No se encontro un pedido con ese numero.",
            "order_id": str(order_id).strip(),
        }

    return {
        "ok": True,
        "order_id": str(order_id).strip(),
        "status": order.get("estado"),
        "products": order.get("productos", []),
        "order": order,
    }


def verificar_elegibilidad_devolucion(order_id: str, product_name: str) -> Dict[str, Any]:
    """
    Verify whether a product from an order is eligible for return.

    Args:
        order_id: EcoMarket order identifier.
        product_name: Product name or partial product description from the user.

    Returns:
        A structured eligibility result for the return agent.
    """
    order_lookup = consultar_pedido(order_id)
    if not order_lookup["ok"]:
        return {
            "ok": False,
            "eligible": False,
            "error_code": order_lookup["error_code"],
            "message": order_lookup["message"],
            "order_id": order_lookup["order_id"],
        }

    order = order_lookup["order"]
    order_status = order.get("estado")

    if _normalize_text(order_status or "") == "cancelado":
        return {
            "ok": False,
            "eligible": False,
            "error_code": "ORDER_CANCELLED",
            "message": "El pedido esta cancelado y no permite generar una devolucion.",
            "order_id": str(order_id).strip(),
            "order_status": order_status,
        }

    ordered_products = order.get("productos", [])
    matched_order_product = _find_best_match(product_name, ordered_products)

    if not matched_order_product:
        return {
            "ok": False,
            "eligible": False,
            "error_code": "PRODUCT_NOT_IN_ORDER",
            "message": "El producto indicado no aparece dentro del pedido.",
            "order_id": str(order_id).strip(),
            "requested_product": product_name,
            "available_products": ordered_products,
        }

    policies = _load_return_policies()
    policy_names = [policy["name"] for policy in policies]
    matched_policy_name = _find_best_match(matched_order_product, policy_names)

    if not matched_policy_name:
        return {
            "ok": False,
            "eligible": False,
            "error_code": "RETURN_POLICY_NOT_FOUND",
            "message": "No hay una politica de devolucion registrada para ese producto.",
            "order_id": str(order_id).strip(),
            "matched_product": matched_order_product,
        }

    policy = next(item for item in policies if item["name"] == matched_policy_name)

    if not policy.get("returnable", False):
        return {
            "ok": True,
            "eligible": False,
            "error_code": "PRODUCT_NOT_RETURNABLE",
            "message": "El producto no es elegible para devolucion segun la politica registrada.",
            "order_id": str(order_id).strip(),
            "order_status": order_status,
            "matched_product": matched_order_product,
            "policy_product": policy["name"],
            "category": policy["category"],
            "reason": policy.get("reason"),
        }

    return {
        "ok": True,
        "eligible": True,
        "message": "El producto es elegible para devolucion.",
        "order_id": str(order_id).strip(),
        "order_status": order_status,
        "matched_product": matched_order_product,
        "policy_product": policy["name"],
        "category": policy["category"],
        "return_period_days": policy.get("return_period_days"),
        "conditions": policy.get("conditions"),
    }


def generar_etiqueta_devolucion(order_id: str, product_name: str) -> Dict[str, Any]:
    """
    Generate a simulated return label for an eligible return.

    Args:
        order_id: EcoMarket order identifier.
        product_name: Product name or partial product description from the user.

    Returns:
        A structured label result or a controlled rejection reason.
    """
    eligibility = verificar_elegibilidad_devolucion(order_id, product_name)

    if not eligibility.get("eligible"):
        return {
            "ok": False,
            "label_generated": False,
            "error_code": eligibility.get("error_code", "RETURN_NOT_ELIGIBLE"),
            "message": "No se genero etiqueta porque la devolucion no es elegible.",
            "eligibility": eligibility,
        }

    label_seed = f"{eligibility['order_id']}:{eligibility['matched_product']}"
    label_hash = hashlib.sha1(label_seed.encode("utf-8")).hexdigest()[:8].upper()
    return_id = f"RET-{eligibility['order_id']}-{label_hash}"

    return {
        "ok": True,
        "label_generated": True,
        "return_id": return_id,
        "order_id": eligibility["order_id"],
        "product": eligibility["matched_product"],
        "carrier": "EcoExpress Returns",
        "label_url": f"https://returns.ecomarket.com/labels/{return_id}.pdf",
        "instructions": [
            "Empaca el producto cumpliendo las condiciones de devolucion.",
            "Incluye todos los accesorios y el empaque original cuando aplique.",
            "Imprime y pega la etiqueta en una zona visible del paquete.",
            "Entrega el paquete a la transportadora indicada.",
        ],
        "eligibility": eligibility,
    }


def registrar_solicitud_devolucion(
    order_id: str,
    product_name: str,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Persist a local audit record for a return request.

    Args:
        order_id: EcoMarket order identifier.
        product_name: Product name or partial product description from the user.
        result: Result returned by an eligibility or label-generation tool.

    Returns:
        A JSON-friendly audit result.
    """
    LOGS_DIR.mkdir(exist_ok=True)

    if RETURN_REQUESTS_PATH.exists():
        records = _load_json(RETURN_REQUESTS_PATH)
    else:
        records = []

    audit_id_seed = f"{datetime.now().isoformat()}:{order_id}:{product_name}"
    audit_id = hashlib.sha1(audit_id_seed.encode("utf-8")).hexdigest()[:12].upper()

    record = {
        "audit_id": audit_id,
        "created_at": datetime.now().isoformat(),
        "order_id": str(order_id).strip(),
        "requested_product": product_name,
        "result_ok": result.get("ok", False),
        "error_code": result.get("error_code"),
        "label_generated": result.get("label_generated", False),
        "return_id": result.get("return_id"),
        "result": result,
    }
    records.append(record)

    with open(RETURN_REQUESTS_PATH, "w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)

    return {
        "ok": True,
        "audit_id": audit_id,
        "records_path": str(RETURN_REQUESTS_PATH.relative_to(PROJECT_ROOT)),
    }


def _run_cli() -> None:
    """Run a small command-line interface for manual tool checks."""
    parser = argparse.ArgumentParser(description="EcoMarket return tools")
    parser.add_argument("action", choices=["order", "eligibility", "label"])
    parser.add_argument("--order-id", required=True)
    parser.add_argument("--product", nargs="+", default=[])
    args = parser.parse_args()

    if args.action == "order":
        result = consultar_pedido(args.order_id)
    elif args.action == "eligibility":
        result = verificar_elegibilidad_devolucion(args.order_id, " ".join(args.product))
    else:
        result = generar_etiqueta_devolucion(args.order_id, " ".join(args.product))

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _run_cli()
