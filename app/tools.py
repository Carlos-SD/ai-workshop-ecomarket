"""Agent tools.

Four LangChain tools, exposed to the agent:

1. consultar_estado_pedido         — RAG-as-tool: order lookup.
2. consultar_politica_devolucion   — RAG-as-tool: policy lookup.
3. verificar_elegibilidad_devolucion — Action tool: eligibility decision.
4. generar_etiqueta_devolucion     — Action tool: issue a return label.

Design rules (per PHASE3.md §6):
- All tools return JSON-serializable dicts. The LLM reads these directly.
- Errors are returned, not raised — the agent should handle them in conversation.
- The label-generation tool re-runs the eligibility check internally (defense in
  depth). The LLM cannot bypass business rules by skipping the eligibility tool.
- Every invocation is logged through app.logger.log_tool_call.
"""
from __future__ import annotations

import hashlib
import random
import string
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from .config import get_today
from .data_access import find_policy, get_order, product_in_order
from .logger import log_tool_call


# ============================================================================
# Pydantic input schemas (used by LangChain to render JSON schemas for Gemini)
# ============================================================================
class OrderLookupInput(BaseModel):
    order_id: str = Field(..., description="The order number, e.g. '12345'. Strings only.")


class PolicyLookupInput(BaseModel):
    product_name: str = Field(
        ...,
        description="The product name to look up. Fuzzy matching is supported, so partial names work.",
    )


class EligibilityInput(BaseModel):
    order_id: str = Field(..., description="The order containing the product to return.")
    product_name: str = Field(..., description="The specific product the customer wants to return.")


class LabelInput(BaseModel):
    order_id: str = Field(..., description="The order containing the product to return.")
    product_name: str = Field(..., description="The specific product being returned.")
    return_reason: str = Field(
        ...,
        description=(
            "Customer-provided reason for the return (e.g. 'defective', 'wrong item', "
            "'changed my mind'). Free text."
        ),
    )


# ============================================================================
# Tool 1: consultar_estado_pedido
# ============================================================================
@tool("consultar_estado_pedido", args_schema=OrderLookupInput)
def consultar_estado_pedido(order_id: str) -> dict:
    """Look up the current status and details of an EcoMarket order.

    Use this when the customer asks about delivery progress, tracking, expected
    arrival date, or what's inside an order. Returns the full order record on
    success, or a not-found marker. Does NOT decide return eligibility — use
    verificar_elegibilidad_devolucion for that.
    """
    with log_tool_call("consultar_estado_pedido", {"order_id": order_id}) as rec:
        order_id = str(order_id).strip()
        if not order_id or not order_id.isdigit():
            out = {
                "found": False,
                "error": "Invalid order ID format. Expected a numeric string.",
                "order_id": order_id,
            }
            rec["outputs"] = out
            return out

        order = get_order(order_id)
        if order is None:
            out = {"found": False, "order_id": order_id, "error": "Order not found"}
            rec["outputs"] = out
            return out

        out = {"found": True, **order}
        rec["outputs"] = out
        return out


# ============================================================================
# Tool 2: consultar_politica_devolucion
# ============================================================================
@tool("consultar_politica_devolucion", args_schema=PolicyLookupInput)
def consultar_politica_devolucion(product_name: str) -> dict:
    """Look up the return policy for a product by name.

    Use this for generic policy questions like 'Can I return X?' or 'How long is
    the return window for Y?'. This tool answers the policy question in the
    abstract — it does NOT consider any specific order. For order-specific
    eligibility, use verificar_elegibilidad_devolucion.
    """
    with log_tool_call("consultar_politica_devolucion", {"product_name": product_name}) as rec:
        policy = find_policy(product_name)
        if policy is None:
            out = {
                "found": False,
                "product_name": product_name,
                "error": "Product not found in policy database",
            }
            rec["outputs"] = out
            return out

        # Build a clean response — drop internal fields we don't need to expose.
        out = {
            "found": True,
            "product_name": policy["name"],
            "category": policy.get("category"),
            "returnable": policy["returnable"],
            "match_type": policy.get("match_type"),
            "match_score": policy.get("match_score"),
        }
        if policy["returnable"]:
            out["return_period_days"] = policy.get("return_period_days")
            out["conditions"] = policy.get("conditions")
        else:
            out["reason"] = policy.get("reason")
        rec["outputs"] = out
        return out


# ============================================================================
# Internal: pure eligibility check (shared by tool 3 and tool 4)
# ============================================================================
def _check_eligibility(order_id: str, product_name: str, today: Optional[date] = None) -> dict:
    """Pure eligibility check. No logging — callers handle logging.

    This function is also called from inside generar_etiqueta_devolucion as
    defense in depth, so the business rule cannot be bypassed by the LLM.
    """
    today = today or get_today()

    # 1. Order exists?
    order = get_order(order_id)
    if order is None:
        return {
            "is_eligible": False,
            "order_id": order_id,
            "product_name": product_name,
            "reason_code": "ORDER_NOT_FOUND",
            "reason": "Order not found in the system",
            "human_friendly_explanation": (
                f"I couldn't find order #{order_id}. Could you double-check the number?"
            ),
        }

    # 2. Order delivered?
    if order.get("status") != "Delivered":
        return {
            "is_eligible": False,
            "order_id": order_id,
            "product_name": product_name,
            "reason_code": "ORDER_NOT_DELIVERED",
            "reason": f"Order status is '{order.get('status')}', not 'Delivered'",
            "human_friendly_explanation": (
                f"Order #{order_id} hasn't been delivered yet — it's currently "
                f"{order.get('status', 'unknown')}. Returns can only be started after delivery."
            ),
            "order_status": order.get("status"),
        }

    # 3. Product is part of the order?
    canonical_product = product_in_order(order, product_name)
    if canonical_product is None:
        return {
            "is_eligible": False,
            "order_id": order_id,
            "product_name": product_name,
            "reason_code": "PRODUCT_NOT_IN_ORDER",
            "reason": "Requested product is not part of this order",
            "human_friendly_explanation": (
                f"I don't see '{product_name}' in order #{order_id}. "
                f"That order contains: {', '.join(order.get('products', []))}."
            ),
            "order_products": order.get("products", []),
        }

    # 4. Policy exists?
    policy = find_policy(canonical_product)
    if policy is None:
        return {
            "is_eligible": False,
            "order_id": order_id,
            "product_name": canonical_product,
            "reason_code": "POLICY_NOT_FOUND",
            "reason": "No return policy on file for this product",
            "human_friendly_explanation": (
                f"I don't have a return policy registered for '{canonical_product}'. "
                "Please contact support@ecomarket.com so a human can help."
            ),
        }

    # 5. Returnable category?
    if not policy["returnable"]:
        return {
            "is_eligible": False,
            "order_id": order_id,
            "product_name": canonical_product,
            "reason_code": "NON_RETURNABLE_CATEGORY",
            "reason": policy.get("reason", "Product is non-returnable per policy"),
            "human_friendly_explanation": (
                f"Unfortunately {canonical_product} can't be returned. {policy.get('reason', '')}"
            ),
        }

    # 6. Within return window?
    delivery_str = order.get("delivery_date")
    if not delivery_str:
        return {
            "is_eligible": False,
            "order_id": order_id,
            "product_name": canonical_product,
            "reason_code": "MISSING_DELIVERY_DATE",
            "reason": "Order is marked delivered but has no delivery_date",
            "human_friendly_explanation": (
                "Our records show this order as delivered but the delivery date is missing. "
                "Please contact support@ecomarket.com."
            ),
        }
    try:
        delivery_date = datetime.strptime(delivery_str, "%Y-%m-%d").date()
    except ValueError:
        return {
            "is_eligible": False,
            "order_id": order_id,
            "product_name": canonical_product,
            "reason_code": "MISSING_DELIVERY_DATE",
            "reason": f"Invalid delivery_date format: {delivery_str}",
            "human_friendly_explanation": "Internal data error. Please contact support@ecomarket.com.",
        }

    days_since_delivery = (today - delivery_date).days
    window = policy.get("return_period_days", 0)
    days_remaining = window - days_since_delivery

    if days_remaining < 0:
        return {
            "is_eligible": False,
            "order_id": order_id,
            "product_name": canonical_product,
            "reason_code": "RETURN_WINDOW_EXPIRED",
            "reason": f"{days_since_delivery} days since delivery; window is {window} days",
            "human_friendly_explanation": (
                f"The {window}-day return window for {canonical_product} closed "
                f"{abs(days_remaining)} day(s) ago (delivered on {delivery_str}). "
                "If the product is defective, please contact support to discuss a warranty claim."
            ),
            "delivery_date": delivery_str,
            "days_since_delivery": days_since_delivery,
            "return_period_days": window,
        }

    # 7. Eligible.
    return {
        "is_eligible": True,
        "order_id": order_id,
        "product_name": canonical_product,
        "delivery_date": delivery_str,
        "days_since_delivery": days_since_delivery,
        "return_period_days": window,
        "days_remaining": days_remaining,
        "conditions": policy.get("conditions"),
        "next_step": "Call generar_etiqueta_devolucion to issue the prepaid label.",
    }


# ============================================================================
# Tool 3: verificar_elegibilidad_devolucion
# ============================================================================
@tool("verificar_elegibilidad_devolucion", args_schema=EligibilityInput)
def verificar_elegibilidad_devolucion(order_id: str, product_name: str) -> dict:
    """Decide whether a specific product inside a specific order is eligible for return RIGHT NOW.

    Combines: order existence, delivery status, product membership, return-policy
    category, and time-since-delivery. Returns a structured verdict with
    `is_eligible` (bool) and a `reason_code`. ALWAYS call this BEFORE
    generar_etiqueta_devolucion. If is_eligible is False, do NOT call the label
    tool; instead, explain the reason to the customer using
    `human_friendly_explanation`.
    """
    with log_tool_call(
        "verificar_elegibilidad_devolucion",
        {"order_id": order_id, "product_name": product_name},
    ) as rec:
        verdict = _check_eligibility(order_id, product_name)
        rec["outputs"] = verdict
        return verdict


# ============================================================================
# Tool 4: generar_etiqueta_devolucion
# ============================================================================
def _generate_label_id(order_id: str, product_name: str) -> str:
    """Deterministic-looking but unique label ID: RET-<order>-<4-char hash>."""
    seed = f"{order_id}|{product_name}|{datetime.now().isoformat()}"
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:4].upper()
    return f"RET-{order_id}-{h}"


def _generate_tracking_number(carrier: str = "EcoExpress") -> str:
    prefix = "EE" if carrier == "EcoExpress" else "GS"
    digits = "".join(random.choices(string.digits, k=10))
    return f"{prefix}{digits}"


@tool("generar_etiqueta_devolucion", args_schema=LabelInput)
def generar_etiqueta_devolucion(
    order_id: str, product_name: str, return_reason: str
) -> dict:
    """Issue a simulated prepaid return shipping label.

    This is the only action with side effects. Use it ONLY AFTER
    verificar_elegibilidad_devolucion returns is_eligible=True for the same
    order+product. The tool re-runs the eligibility check internally as defense
    in depth — if eligibility fails here, the label will NOT be issued, even if
    you call this tool directly.

    Returns a label record with label_id, tracking number, carrier, expiration,
    and step-by-step pickup instructions.
    """
    inputs = {
        "order_id": order_id,
        "product_name": product_name,
        "return_reason": return_reason,
    }
    with log_tool_call("generar_etiqueta_devolucion", inputs) as rec:
        # Defense in depth: re-run eligibility.
        verdict = _check_eligibility(order_id, product_name)
        if not verdict.get("is_eligible"):
            out = {
                "success": False,
                "reason_code": "NOT_ELIGIBLE",
                "reason": (
                    "Eligibility re-check failed at label-generation time. "
                    "The agent should not have called this tool."
                ),
                "eligibility_details": verdict,
            }
            rec["outputs"] = out
            rec["success"] = False
            return out

        canonical_product = verdict["product_name"]
        order = get_order(order_id) or {}
        carrier = order.get("carrier", "EcoExpress")
        now = datetime.now(timezone.utc)

        label = {
            "success": True,
            "label_id": _generate_label_id(order_id, canonical_product),
            "tracking_number": _generate_tracking_number(carrier),
            "carrier": carrier,
            "order_id": order_id,
            "product_name": canonical_product,
            "return_reason": return_reason,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(days=7)).isoformat(),
            "instructions": [
                "Pack the product in its original packaging when possible.",
                "Print the label and securely attach it to the package.",
                f"Drop off at any {carrier} collection point within 7 days.",
                "Refund will be processed within 5–7 business days after we receive it.",
            ],
            "label_url": f"https://labels.ecomarket.com/{_generate_label_id(order_id, canonical_product)}.pdf",
        }
        rec["outputs"] = label
        return label


# ============================================================================
# Export list (used by the agent factory)
# ============================================================================
ALL_TOOLS = [
    consultar_estado_pedido,
    consultar_politica_devolucion,
    verificar_elegibilidad_devolucion,
    generar_etiqueta_devolucion,
]
