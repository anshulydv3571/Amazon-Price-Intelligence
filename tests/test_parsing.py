import pytest

from parsing import ScrapeError, clean_url, is_blocked, parse_price, parse_product_html

PRODUCT_HTML = """
<html><body>
  <span id="productTitle">  Test Wireless Earbuds  </span>
  <div id="corePriceDisplay_desktop_feature_div">
    <span class="a-price a-text-price"><span class="a-offscreen">₹3,999.00</span></span>
    <span class="a-price"><span class="a-offscreen">₹1,299.00</span></span>
  </div>
</body></html>
"""


@pytest.mark.parametrize("text,expected", [
    ("₹1,299.00", 1299.0), ("₹ 54,999", 54999.0), ("Rs. 499", 499.0),
    ("M.R.P.: ₹1,299", 1299.0), ("", None), (None, None), ("Currently unavailable", None),
])
def test_parse_price(text, expected):
    assert parse_price(text) == expected


def test_parse_product_html_uses_current_price_not_mrp():
    data = parse_product_html(PRODUCT_HTML)
    assert data == {"title": "Test Wireless Earbuds", "price": 1299.0}


def test_captcha_page_is_detected():
    html = "<html>Enter the characters you see below</html>"
    assert is_blocked(html)
    with pytest.raises(ScrapeError):
        parse_product_html(html)


def test_missing_price_raises():
    with pytest.raises(ScrapeError):
        parse_product_html('<span id="productTitle">Thing</span>')


def test_clean_url():
    long = "https://www.amazon.in/Some-Product-Name/dp/B0ABCDE123/ref=sr_1_1?keywords=x&qid=1"
    assert clean_url(long) == "https://www.amazon.in/dp/B0ABCDE123"
    assert clean_url("amazon.in/gp/product/b0abcde123") == "https://amazon.in/dp/B0ABCDE123"
    assert clean_url("https://amzn.in/d/abc123") == "https://amzn.in/d/abc123"
    with pytest.raises(ValueError):
        clean_url("https://example.com/dp/B0ABCDE123")
    with pytest.raises(ValueError):
        clean_url("https://www.amazon.in/")
