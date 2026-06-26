from sales_showcase.marketplace import FakeMarketplaceClient
from sales_showcase.models import Condition, InventoryItem
from sales_showcase.orchestrator import cross_post

ITEM = InventoryItem(
    sku="SKU-9",
    title="Wool Coat",
    brand="Ashford",
    category="Outerwear",
    condition=Condition.GOOD,
    price_usd=95.0,
    cost_usd=30.0,
)


def _noop(_seconds: float) -> None:  # no real sleeping in tests
    pass


def test_all_success():
    clients = [FakeMarketplaceClient("a"), FakeMarketplaceClient("b")]
    report = cross_post(ITEM, clients, sleep=_noop)
    assert report.ok_count == 2
    assert report.failed_count == 0
    assert report.fully_listed


def test_transient_is_retried_then_succeeds():
    client = FakeMarketplaceClient("a", transient_fail=("SKU-9",), transient_count=2)
    report = cross_post(ITEM, [client], max_attempts=3, sleep=_noop)
    result = report.results[0]
    assert result.ok
    assert result.attempts == 3  # failed twice, succeeded on the third


def test_transient_exhausts_attempts():
    client = FakeMarketplaceClient("a", transient_fail=("SKU-9",), transient_count=9)
    report = cross_post(ITEM, [client], max_attempts=3, sleep=_noop)
    result = report.results[0]
    assert not result.ok
    assert result.attempts == 3
    assert "exhausted" in (result.error or "")


def test_permanent_fails_fast_without_retry():
    client = FakeMarketplaceClient("a", hard_fail=("SKU-9",))
    report = cross_post(ITEM, [client], max_attempts=3, sleep=_noop)
    result = report.results[0]
    assert not result.ok
    assert result.attempts == 1
    assert "permanent" in (result.error or "")


def test_idempotent_skip():
    client = FakeMarketplaceClient("a")
    report = cross_post(
        ITEM, [client], already_posted=frozenset({("SKU-9", "a")}), sleep=_noop
    )
    result = report.results[0]
    assert result.skipped
    assert report.ok_count == 0
    assert report.skipped_count == 1


def test_partial_failure_is_reported():
    clients = [FakeMarketplaceClient("a"), FakeMarketplaceClient("b", hard_fail=("SKU-9",))]
    report = cross_post(ITEM, clients, sleep=_noop)
    assert report.ok_count == 1
    assert report.failed_count == 1
    assert not report.fully_listed
