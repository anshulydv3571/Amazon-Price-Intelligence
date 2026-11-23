"""Background checker: scrape every active product, store the price, send alerts.

    python worker.py --once          # one cycle, then exit (good for cron / Task Scheduler)
    python worker.py                 # loop forever, every CHECK_INTERVAL_MINUTES
    python worker.py --interval 30   # loop every 30 minutes
"""
from __future__ import annotations

import argparse
import logging
import random
import time

import pandas as pd

import config
import db
from notifier import send_price_alert
from parsing import ScrapeError
from scraper import AmazonScraper

log = logging.getLogger("worker")


def _clean(value):
    return None if pd.isna(value) else value


def maybe_alert(product: dict, price: float) -> None:
    """Email once per new low at/below target; re-arm when the price rises above target."""
    target = _clean(product["target_price"])
    email = _clean(product["email"])
    last_alert = _clean(product["last_alert_price"])
    if target is None:
        return

    if price > target:
        if last_alert is not None:
            db.set_last_alert(product["id"], None)  # re-arm
        return

    if not email:
        return
    if last_alert is None or price < last_alert:
        try:
            send_price_alert(email, product["title"], product["url"], price, target)
            db.set_last_alert(product["id"], price)
            log.info("Alert sent to %s for %s at %.2f", email, product["title"][:40], price)
        except Exception as exc:  # SMTP problems must not stop the cycle
            log.error("Could not send alert: %s", exc)


def run_cycle() -> None:
    products = db.get_products(active_only=True)
    if products.empty:
        log.info("No active products to check.")
        return

    log.info("Checking %d product(s)...", len(products))
    with AmazonScraper() as scraper:
        for product in products.to_dict("records"):
            try:
                data = scraper.fetch(product["url"])
            except ScrapeError as exc:
                log.warning("Skipped %s: %s", product["title"][:40], exc)
                continue
            db.add_price(product["id"], data["price"])
            log.info("%s -> %s%.2f", product["title"][:40], config.CURRENCY, data["price"])
            maybe_alert(product, data["price"])
            time.sleep(random.uniform(*config.REQUEST_DELAY_RANGE))


def main() -> None:
    parser = argparse.ArgumentParser(description="Amazon price checker")
    parser.add_argument("--once", action="store_true", help="run a single cycle and exit")
    parser.add_argument("--interval", type=int, default=config.CHECK_INTERVAL_MINUTES,
                        help="minutes between cycles (default from .env)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        while True:
            run_cycle()
            if args.once:
                break
            log.info("Sleeping %d minutes. Ctrl+C to stop.", args.interval)
            time.sleep(args.interval * 60)
    except KeyboardInterrupt:
        log.info("Stopped.")


if __name__ == "__main__":
    main()
