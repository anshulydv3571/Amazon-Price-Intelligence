"""Selenium wrapper: loads a product page in headless Chrome, hands the HTML to parsing.py."""
from __future__ import annotations

import random
import time

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options

import config
from parsing import ScrapeError, parse_product_html

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class AmazonScraper:
    """Use as a context manager so one browser is reused for a whole check cycle."""

    def __init__(self, headless: bool = config.HEADLESS, page_timeout: int = 30):
        self.headless = headless
        self.page_timeout = page_timeout
        self.driver = None

    def start(self) -> None:
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--window-size=1366,900")
        options.add_argument("--lang=en-IN")
        options.add_argument(f"--user-agent={USER_AGENT}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        # Selenium 4.6+ downloads the matching ChromeDriver automatically.
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(self.page_timeout)

    def fetch(self, url: str, retries: int = 2) -> dict:
        """Return {'title', 'price'} or raise ScrapeError after `retries` extra attempts."""
        if self.driver is None:
            self.start()
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                self.driver.get(url)
                time.sleep(random.uniform(2, 4))  # let dynamic content render
                return parse_product_html(self.driver.page_source)
            except (ScrapeError, WebDriverException) as exc:
                last_error = exc
                time.sleep(random.uniform(3, 6) * (attempt + 1))  # back off before retrying
        raise ScrapeError(f"Failed after {retries + 1} attempts: {last_error}")

    def close(self) -> None:
        if self.driver is not None:
            self.driver.quit()
            self.driver = None

    def __enter__(self) -> "AmazonScraper":
        self.start()
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
