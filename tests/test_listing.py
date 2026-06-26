from sales_showcase.listing import (
    ListingPolicy,
    build_listing,
    build_tags,
    build_title,
)
from sales_showcase.models import Condition, InventoryItem

ITEM = InventoryItem(
    sku="SKU-1",
    title="Denim Trucker Jacket",
    brand="Northbound",
    category="Outerwear",
    condition=Condition.GOOD,
    price_usd=68.0,
    cost_usd=22.0,
    size="M",
    color="Indigo",
)


def test_title_includes_brand_and_details():
    title = build_title(ITEM, ListingPolicy("m"))
    assert "Northbound" in title
    assert "Denim Trucker Jacket" in title
    assert "M" in title and "Indigo" in title


def test_title_respects_max_length():
    title = build_title(ITEM, ListingPolicy("m", max_title=20))
    assert len(title) <= 20


def test_title_can_exclude_brand():
    title = build_title(ITEM, ListingPolicy("m", include_brand_in_title=False))
    assert not title.startswith("Northbound")


def test_tags_are_capped_and_deduped():
    tags = build_tags(ITEM, ListingPolicy("m", max_tags=3))
    assert len(tags) <= 3
    assert len(set(tags)) == len(tags)


def test_build_listing_is_deterministic():
    a = build_listing(ITEM, ListingPolicy("m"))
    b = build_listing(ITEM, ListingPolicy("m"))
    assert a == b
    assert a.price_usd == 68.0
    assert a.marketplace == "m"
