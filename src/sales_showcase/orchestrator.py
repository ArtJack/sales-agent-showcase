"""Cross-posting orchestrator.

Takes one inventory item and a set of marketplace adapters, renders a listing
for each, and publishes them — with bounded retries on transient errors,
fast-fail on permanent ones, and idempotency so re-running never double-posts.

This is the part that turns "I can call one marketplace API" into "I can keep an
item listed correctly across many marketplaces, unattended."
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field

from .listing import ListingPolicy, build_listing
from .marketplace import MarketplaceClient, PermanentError, TransientError
from .models import InventoryItem, PublishResult


def _fake_latency_ms(marketplace: str, sku: str) -> int:
    """Deterministic pseudo-latency so demo/test output is stable."""
    digest = hashlib.sha1(f"{marketplace}:{sku}".encode()).hexdigest()
    return 30 + int(digest, 16) % 170  # 30–199 ms


@dataclass
class CrossPostReport:
    item_sku: str
    results: list[PublishResult] = field(default_factory=list)

    @property
    def ok_count(self) -> int:
        return sum(1 for r in self.results if r.ok and not r.skipped)

    @property
    def skipped_count(self) -> int:
        return sum(1 for r in self.results if r.skipped)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.ok)

    @property
    def fully_listed(self) -> bool:
        return self.failed_count == 0


def _publish_with_retry(
    client: MarketplaceClient,
    listing,
    *,
    max_attempts: int,
    backoff_base: float,
    sleep: Callable[[float], None],
) -> PublishResult:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            listing_id = client.publish(listing)
        except PermanentError as exc:
            return PublishResult(
                sku=listing.sku,
                marketplace=client.name,
                ok=False,
                error=f"permanent: {exc}",
                attempts=attempt,
            )
        except TransientError as exc:
            last_error = exc
            if attempt < max_attempts:
                sleep(backoff_base * (2 ** (attempt - 1)))  # exponential backoff
            continue
        else:
            return PublishResult(
                sku=listing.sku,
                marketplace=client.name,
                ok=True,
                listing_id=listing_id,
                attempts=attempt,
                latency_ms=_fake_latency_ms(client.name, listing.sku),
            )
    return PublishResult(
        sku=listing.sku,
        marketplace=client.name,
        ok=False,
        error=f"transient (exhausted after {max_attempts}): {last_error}",
        attempts=max_attempts,
    )


def cross_post(
    item: InventoryItem,
    clients: Iterable[MarketplaceClient],
    *,
    policies: Mapping[str, ListingPolicy] | None = None,
    already_posted: frozenset[tuple[str, str]] = frozenset(),
    max_attempts: int = 3,
    backoff_base: float = 0.0,
    sleep: Callable[[float], None] = time.sleep,
) -> CrossPostReport:
    """Publish `item` to every client.

    `already_posted` is a set of (sku, marketplace) pairs that are already live —
    those are skipped, which is what makes re-running the whole inventory safe.
    `backoff_base=0.0` keeps demos and tests instant; production uses a real base.
    """
    policies = policies or {}
    report = CrossPostReport(item_sku=item.sku)
    for client in clients:
        if (item.sku, client.name) in already_posted:
            report.results.append(
                PublishResult(
                    sku=item.sku,
                    marketplace=client.name,
                    ok=True,
                    skipped=True,
                    error="already listed",
                    attempts=0,
                )
            )
            continue
        policy = policies.get(client.name, ListingPolicy(client.name))
        listing = build_listing(item, policy)
        report.results.append(
            _publish_with_retry(
                client,
                listing,
                max_attempts=max_attempts,
                backoff_base=backoff_base,
                sleep=sleep,
            )
        )
    return report
