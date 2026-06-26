"""A tiny SQLite ledger of what's been published where.

The production system persists listing state in a real database (migrations, a
richer schema); this is a stdlib-only stand-in that captures the one property
that matters for correctness: which (sku, marketplace) pairs are already live, so
the orchestrator can skip them on the next run instead of double-posting.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from .models import PublishResult

_SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    sku         TEXT NOT NULL,
    marketplace TEXT NOT NULL,
    listing_id  TEXT,
    ok          INTEGER NOT NULL,
    error       TEXT,
    PRIMARY KEY (sku, marketplace)
);
"""


class Ledger:
    def __init__(self, path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(path)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def record(self, results: Iterable[PublishResult]) -> None:
        with self._conn:
            for r in results:
                if r.skipped:
                    continue
                self._conn.execute(
                    "INSERT INTO listings (sku, marketplace, listing_id, ok, error) "
                    "VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT(sku, marketplace) DO UPDATE SET "
                    "listing_id=excluded.listing_id, ok=excluded.ok, error=excluded.error",
                    (r.sku, r.marketplace, r.listing_id, int(r.ok), r.error),
                )

    def posted_keys(self) -> frozenset[tuple[str, str]]:
        """(sku, marketplace) pairs that are successfully live."""
        rows = self._conn.execute(
            "SELECT sku, marketplace FROM listings WHERE ok = 1"
        ).fetchall()
        return frozenset((sku, mk) for sku, mk in rows)

    def close(self) -> None:
        self._conn.close()
