from datetime import datetime, timedelta


def test_add_product_is_idempotent_per_url(sqlite_db):
    db = sqlite_db
    a = db.add_product("https://x/dp/A", "Thing", 100, "a@b.com")
    b = db.add_product("https://x/dp/A", "Thing v2", 90, None)
    assert a == b
    products = db.get_products()
    assert len(products) == 1 and products.loc[0, "title"] == "Thing v2"


def test_history_stats_and_drops(sqlite_db):
    db = sqlite_db
    pid = db.add_product("https://x/dp/A", "Thing", 100, None)
    t0 = datetime(2026, 1, 1)
    for i, price in enumerate([100, 120, 90, 95]):
        db.add_price(pid, price, t0 + timedelta(hours=i))

    hist = db.get_history(pid)
    assert hist["price"].tolist() == [100, 120, 90, 95]

    stats = db.latest_stats().iloc[0]
    assert stats["current_price"] == 95 and stats["min_price"] == 90
    assert stats["max_price"] == 120 and stats["checks"] == 4

    drops = db.biggest_drops()
    assert len(drops) == 1
    assert drops.iloc[0]["change_pct"] == -25.0   # 120 -> 90


def test_delete_removes_history(sqlite_db):
    db = sqlite_db
    pid = db.add_product("https://x/dp/A", "Thing")
    db.add_price(pid, 10)
    db.delete_product(pid)
    assert db.get_products().empty and db.get_all_history().empty
