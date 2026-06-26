"""Marketplace adapter interface + a fake adapter for the demo and tests.

In the production system, each marketplace gets a real adapter. Those adapters
are proprietary client work and stay private. Every adapter implements the same
tiny `MarketplaceClient` protocol, so the orchestrator never knows or cares which
marketplace it is talking to.

`FakeMarketplaceClient` is the *only* adapter in this public repo. It performs no
network I/O and holds no credentials — it just simulates success, transient
failure (to exercise retries), and permanent rejection (to exercise
partial-failure reporting).
"""

from __future__ import annotations

import hashlib
from typing import Protocol, runtime_checkable

from .models import Listing


class TransientError(Exception):
    """A retriable failure (rate limit, timeout, 5xx)."""


class PermanentError(Exception):
    """A non-retriable failure (validation/policy rejection)."""


@runtime_checkable
class MarketplaceClient(Protocol):
    name: str

    def publish(self, listing: Listing) -> str:
        """Publish a listing and return the marketplace's listing id.

        Raises TransientError for retriable problems and PermanentError for
        non-retriable ones. The orchestrator owns the retry policy.
        """
        ...


class FakeMarketplaceClient:
    """A stub adapter. No network, no auth — a stand-in for a real integration."""

    def __init__(
        self,
        name: str,
        *,
        transient_fail: tuple[str, ...] = (),
        transient_count: int = 1,
        hard_fail: tuple[str, ...] = (),
    ) -> None:
        self.name = name
        # sku -> remaining number of transient failures before it succeeds
        self._transient: dict[str, int] = dict.fromkeys(transient_fail, transient_count)
        self._hard: set[str] = set(hard_fail)

    def publish(self, listing: Listing) -> str:
        sku = listing.sku
        if sku in self._hard:
            raise PermanentError(
                f"{self.name}: rejected {sku} (failed listing validation)"
            )
        remaining = self._transient.get(sku, 0)
        if remaining > 0:
            self._transient[sku] = remaining - 1
            raise TransientError(f"{self.name}: temporary error publishing {sku}")
        digest = hashlib.sha1(f"{self.name}:{sku}".encode()).hexdigest()[:10]
        return f"{self.name}-{digest}"
