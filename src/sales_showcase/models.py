"""Normalized domain model shared across every marketplace.

The whole point of a cross-posting system is that an item is described *once*, in
a marketplace-agnostic shape, and each adapter renders it into that
marketplace's listing format. These dataclasses are that single source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Condition(str, Enum):
    NEW = "new"
    LIKE_NEW = "like_new"
    GOOD = "good"
    FAIR = "fair"


@dataclass(frozen=True)
class InventoryItem:
    """One physical item to sell, described independently of any marketplace."""

    sku: str
    title: str
    brand: str
    category: str
    condition: Condition
    price_usd: float
    cost_usd: float
    size: str | None = None
    color: str | None = None
    photos: tuple[str, ...] = ()
    notes: str = ""

    @property
    def margin_usd(self) -> float:
        return round(self.price_usd - self.cost_usd, 2)


@dataclass(frozen=True)
class Listing:
    """An InventoryItem rendered for one marketplace's constraints."""

    sku: str
    marketplace: str
    title: str
    body: str
    price_usd: float
    tags: tuple[str, ...]


@dataclass(frozen=True)
class PublishResult:
    """The outcome of trying to publish one listing to one marketplace."""

    sku: str
    marketplace: str
    ok: bool
    listing_id: str | None = None
    error: str | None = None
    attempts: int = 1
    latency_ms: int = 0
    skipped: bool = False
