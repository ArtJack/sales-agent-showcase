from sales_showcase.ledger import Ledger
from sales_showcase.models import PublishResult


def test_ledger_tracks_only_successful_keys():
    ledger = Ledger()
    ledger.record(
        [
            PublishResult(sku="S1", marketplace="a", ok=True, listing_id="x"),
            PublishResult(sku="S1", marketplace="b", ok=False, error="boom"),
        ]
    )
    assert ledger.posted_keys() == frozenset({("S1", "a")})


def test_ledger_upsert_is_idempotent():
    ledger = Ledger()
    ledger.record([PublishResult(sku="S1", marketplace="a", ok=False, error="boom")])
    ledger.record([PublishResult(sku="S1", marketplace="a", ok=True, listing_id="x")])
    assert ledger.posted_keys() == frozenset({("S1", "a")})


def test_ledger_ignores_skipped():
    ledger = Ledger()
    ledger.record([PublishResult(sku="S1", marketplace="a", ok=True, skipped=True)])
    assert ledger.posted_keys() == frozenset()
