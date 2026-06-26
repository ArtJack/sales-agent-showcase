"""Deterministic listing generation.

Each marketplace has its own constraints (title length, tag count, whether the
brand belongs in the title). Generating listings with pure, deterministic rules
— rather than free-form LLM output on a field that affects a real sale — means
the result is testable and never surprises the seller. The production system
adds an optional LLM pass for *description prose only*, gated behind review; the
title, price, and tags stay rule-based.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import InventoryItem, Listing


@dataclass(frozen=True)
class ListingPolicy:
    """Per-marketplace formatting rules."""

    marketplace: str
    max_title: int = 80
    max_tags: int = 10
    include_brand_in_title: bool = True


def _truncate(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def build_title(item: InventoryItem, policy: ListingPolicy) -> str:
    parts: list[str] = []
    if policy.include_brand_in_title and item.brand:
        parts.append(item.brand)
    parts.append(item.title)
    details = [d for d in (item.size, item.color) if d]
    if details:
        parts.append("(" + ", ".join(details) + ")")
    return _truncate(" ".join(parts), policy.max_title)


def build_tags(item: InventoryItem, policy: ListingPolicy) -> tuple[str, ...]:
    raw = [
        item.brand,
        item.category,
        item.color or "",
        item.condition.value.replace("_", " "),
        item.size or "",
    ]
    seen: dict[str, None] = {}
    for tag in raw:
        slug = tag.strip().lower()
        if slug:
            seen.setdefault(slug, None)
    return tuple(list(seen)[: policy.max_tags])


def build_body(item: InventoryItem) -> str:
    lines = [
        f"{item.brand} {item.title}".strip(),
        "",
        f"Condition: {item.condition.value.replace('_', ' ').title()}",
    ]
    if item.size:
        lines.append(f"Size: {item.size}")
    if item.color:
        lines.append(f"Color: {item.color}")
    if item.notes:
        lines += ["", item.notes.strip()]
    return "\n".join(lines)


def build_listing(item: InventoryItem, policy: ListingPolicy) -> Listing:
    return Listing(
        sku=item.sku,
        marketplace=policy.marketplace,
        title=build_title(item, policy),
        body=build_body(item),
        price_usd=round(item.price_usd, 2),
        tags=build_tags(item, policy),
    )
