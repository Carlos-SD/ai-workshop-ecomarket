"""Data-access helpers.

Loads the static JSON fixtures and provides a fuzzy product-name matcher used
by several tools. Keeping this isolated means the tools never read files
directly — easier to swap for a real database later.
"""
from __future__ import annotations

import json
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Optional

from .config import DATA_DIR


# --- File loaders (cached) ---------------------------------------------------
@lru_cache(maxsize=1)
def load_orders() -> dict:
    """Load the orders fixture. Keyed by order_id (string)."""
    with open(DATA_DIR / "orders.json", "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_return_policies() -> list[dict]:
    """Load the return policies fixture. Returns the list under 'returnable_products'."""
    with open(DATA_DIR / "return_policies.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("returnable_products", [])


def reload_caches() -> None:
    """Useful for tests when fixtures change between calls."""
    load_orders.cache_clear()
    load_return_policies.cache_clear()


# --- Lookups -----------------------------------------------------------------
def get_order(order_id: str) -> Optional[dict]:
    """Return the order dict (with order_id injected) or None."""
    orders = load_orders()
    order = orders.get(str(order_id).strip())
    if order is None:
        return None
    return {"order_id": str(order_id).strip(), **order}


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_policy(product_name: str, threshold: float = 0.55) -> Optional[dict]:
    """Fuzzy-match a product name against the policy list.

    Returns the best-matching policy if similarity >= threshold, plus an
    injected `match_score` field for observability. Returns None otherwise.

    The threshold is intentionally permissive (0.55) because product names
    in orders and policies don't always align exactly (e.g. "Natural lavender
    soap (pack of 3)" in orders vs "Natural soap" in policies).
    """
    policies = load_return_policies()
    if not product_name:
        return None

    target = product_name.strip()
    # First, try exact (case-insensitive) match.
    for p in policies:
        if p["name"].lower() == target.lower():
            return {**p, "match_score": 1.0, "match_type": "exact"}

    # Then, substring match (either direction).
    for p in policies:
        pname = p["name"].lower()
        tname = target.lower()
        if pname in tname or tname in pname:
            return {**p, "match_score": 0.9, "match_type": "substring"}

    # Finally, fuzzy match.
    scored = [(p, _similarity(p["name"], target)) for p in policies]
    scored.sort(key=lambda x: x[1], reverse=True)
    best, score = scored[0]
    if score >= threshold:
        return {**best, "match_score": round(score, 3), "match_type": "fuzzy"}
    return None


def product_in_order(order: dict, product_name: str, threshold: float = 0.55) -> Optional[str]:
    """Check whether a product (fuzzy match) is part of the given order.

    Returns the canonical product name from the order if found, else None.
    """
    if not order or "products" not in order:
        return None
    target = product_name.strip().lower()
    # Exact / substring first.
    for p in order["products"]:
        if p.lower() == target or target in p.lower() or p.lower() in target:
            return p
    # Fuzzy fallback.
    scored = [(p, _similarity(p, product_name)) for p in order["products"]]
    scored.sort(key=lambda x: x[1], reverse=True)
    best, score = scored[0]
    if score >= threshold:
        return best
    return None
