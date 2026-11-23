"""Pure HTML parsing helpers (no Selenium here, so they are easy to unit-test)."""
from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup


class ScrapeError(Exception):
    """Raised when a page cannot be fetched or parsed into a title + price."""


BLOCK_MARKERS = (
    "enter the characters you see below",
    "type the characters you see in this image",
    "not a robot",
    "/errors/validatecaptcha",
)

# Tried in order; Amazon changes its markup often, so keep several fallbacks.
PRICE_SELECTORS = (
    "#corePriceDisplay_desktop_feature_div span.a-price:not(.a-text-price) span.a-offscreen",
    "#corePrice_feature_div span.a-price span.a-offscreen",
    "span.priceToPay span.a-offscreen",
    "#priceblock_dealprice",
    "#priceblock_ourprice",
    "span.a-price:not(.a-text-price) span.a-offscreen",
    "span.a-price span.a-offscreen",
)


def is_blocked(html: str) -> bool:
    """True if the page looks like a CAPTCHA / robot-check page."""
    lowered = html.lower()
    return any(marker in lowered for marker in BLOCK_MARKERS)


def parse_price(text: str | None) -> float | None:
    """'₹1,299.00' -> 1299.0. Returns None if no number is found."""
    if not text:
        return None
    match = re.search(r"\d[\d,]*(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group().replace(",", ""))
    except ValueError:
        return None


def parse_product_html(html: str) -> dict:
    """Extract {'title': str, 'price': float} from a product page's HTML."""
    if is_blocked(html):
        raise ScrapeError("Amazon returned a CAPTCHA / robot-check page.")

    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.select_one("#productTitle")
    title = title_tag.get_text(strip=True) if title_tag else None

    price = None
    for selector in PRICE_SELECTORS:
        tag = soup.select_one(selector)
        if tag:
            price = parse_price(tag.get_text())
            if price:
                break

    if price is None:  # last resort: whole-number part only
        whole = soup.select_one("span.a-price-whole")
        if whole:
            price = parse_price(whole.get_text())

    if not title:
        raise ScrapeError("Could not find the product title (page layout may have changed).")
    if price is None:
        raise ScrapeError("Could not find a price (item may be unavailable or layout changed).")
    return {"title": title, "price": price}


def clean_url(url: str) -> str:
    """Normalise an Amazon product link to https://<host>/dp/<ASIN>.

    Short links (amzn.in / amzn.to) are returned unchanged; the browser follows them.
    """
    url = url.strip()
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = parsed.netloc.lower()
    if not host or ("amazon." not in host and not host.startswith("amzn.")):
        raise ValueError("That doesn't look like an Amazon product link.")
    if host.startswith("amzn."):
        return f"https://{host}{parsed.path}"
    match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", parsed.path, re.IGNORECASE)
    if not match:
        raise ValueError("Couldn't find the product ID (ASIN) in that link.")
    return f"https://{host}/dp/{match.group(1).upper()}"
