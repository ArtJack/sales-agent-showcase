"""Runnable demo of the cross-posting pipeline on synthetic data.

    python3 demo.py

No install needed (pure stdlib). It loads fake inventory, spins up three fake
marketplace adapters — one configured to fail transiently (to show retries) and
one to reject an item permanently (to show partial-failure handling) — then runs
the orchestrator twice to show idempotent re-posting.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from sales_showcase.ledger import Ledger  # noqa: E402
from sales_showcase.listing import ListingPolicy  # noqa: E402
from sales_showcase.marketplace import FakeMarketplaceClient  # noqa: E402
from sales_showcase.models import Condition, InventoryItem  # noqa: E402
from sales_showcase.orchestrator import CrossPostReport, cross_post  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = HERE / "examples" / "inventory.sample.json"

POLICIES = {
    "marketplace-alpha": ListingPolicy("marketplace-alpha", max_title=80, max_tags=10),
    "marketplace-beta": ListingPolicy("marketplace-beta", max_title=60, max_tags=5),
    "marketplace-gamma": ListingPolicy("marketplace-gamma", max_title=140, max_tags=13),
}


def load_inventory(path: Path) -> list[InventoryItem]:
    items: list[InventoryItem] = []
    for row in json.loads(path.read_text(encoding="utf-8")):
        items.append(
            InventoryItem(
                sku=row["sku"],
                title=row["title"],
                brand=row["brand"],
                category=row["category"],
                condition=Condition(row["condition"]),
                price_usd=row["price_usd"],
                cost_usd=row["cost_usd"],
                size=row.get("size"),
                color=row.get("color"),
                photos=tuple(row.get("photos") or ()),
                notes=row.get("notes", ""),
            )
        )
    return items


def build_clients() -> list[FakeMarketplaceClient]:
    # alpha fails SKU-1002 once (transient → retried); gamma rejects SKU-1005 (permanent).
    return [
        FakeMarketplaceClient("marketplace-alpha", transient_fail=("SKU-1002",), transient_count=1),
        FakeMarketplaceClient("marketplace-beta"),
        FakeMarketplaceClient("marketplace-gamma", hard_fail=("SKU-1005",)),
    ]


def _status(r) -> str:
    if r.skipped:
        return "· already live — skipped"
    if r.ok:
        return f"✓ {r.listing_id}  ({r.attempts} attempt{'s' if r.attempts != 1 else ''}, {r.latency_ms}ms)"
    return f"✗ {r.error}"


def _print_report(item: InventoryItem, report: CrossPostReport) -> None:
    flag = "fully listed" if report.fully_listed else f"{report.failed_count} failed"
    print(
        f"\n{item.sku}  {item.brand} {item.title}"
        f"  →  {report.ok_count} live · {report.skipped_count} skipped · {flag}"
    )
    for r in report.results:
        print(f"    {r.marketplace:<20} {_status(r)}")


def run_pass(label: str, items: list[InventoryItem], clients, ledger: Ledger) -> None:
    print(f"\n{'=' * 70}\n{label}\n{'=' * 70}")
    for item in items:
        report = cross_post(
            item,
            clients,
            policies=POLICIES,
            already_posted=ledger.posted_keys(),
            backoff_base=0.0,
        )
        ledger.record(report.results)
        _print_report(item, report)


def main() -> None:
    items = load_inventory(DATA)
    ledger = Ledger()  # in-memory

    run_pass("PASS 1 — fresh inventory", items, build_clients(), ledger)
    run_pass(
        "PASS 2 — idempotent re-run (everything already live is skipped)",
        items,
        build_clients(),
        ledger,
    )

    print(
        "\nNotes:\n"
        "  • marketplace-alpha hit a transient error on SKU-1002 and retried to success.\n"
        "  • marketplace-gamma permanently rejected SKU-1005 — reported, not retried,\n"
        "    and never marked live, so pass 2 tries it again.\n"
        "  • Everything that succeeded in pass 1 is skipped in pass 2 (no double-posting)."
    )


if __name__ == "__main__":
    main()
