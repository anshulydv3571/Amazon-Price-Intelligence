"""Fill the database with synthetic demo data so the dashboard works without scraping.

    python seed_demo.py

Demo rows are clearly labelled "[DEMO]". Prices are randomly generated, not real Amazon data.
"""
from datetime import datetime, timedelta

import numpy as np

import db

DEMO_PRODUCTS = [
    # title, fake url, typical price, target price
    ("[DEMO] Wireless Earbuds", "https://www.amazon.in/dp/DEMO000001", 2499, 1999),
    ("[DEMO] 27-inch Monitor", "https://www.amazon.in/dp/DEMO000002", 14999, 12500),
    ("[DEMO] Mechanical Keyboard", "https://www.amazon.in/dp/DEMO000003", 3999, 3200),
]
DAYS, CHECKS_PER_DAY = 60, 2


def make_prices(base: float, rng: np.random.Generator) -> np.ndarray:
    n = DAYS * CHECKS_PER_DAY
    prices = np.empty(n)
    level = base
    for i in range(n):
        level += 0.15 * (base - level) + rng.normal(0, base * 0.01)  # mean-reverting noise
        prices[i] = level
    for start in (int(n * 0.30), int(n * 0.75)):  # two "sale" windows
        prices[start:start + 6] *= rng.uniform(0.82, 0.90)
    return np.round(prices)


def main() -> None:
    rng = np.random.default_rng(42)
    now = datetime.now()
    for title, url, base, target in DEMO_PRODUCTS:
        product_id = db.add_product(url, title, target, None)
        if not db.get_history(product_id).empty:
            print(f"Skipping {title}: already has history")
            continue
        prices = make_prices(base, rng)
        step = timedelta(hours=24 / CHECKS_PER_DAY)
        start = now - step * (len(prices) - 1)
        for i, price in enumerate(prices):
            db.add_price(product_id, float(price), start + step * i)
        print(f"Seeded {len(prices)} price points for {title}")


if __name__ == "__main__":
    main()
