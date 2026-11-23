# Amazon Price Tracker — price monitoring + analytics dashboard

Tracks Amazon product prices over time, stores every check in **MySQL**, analyses the history with
**pandas / Matplotlib**, and shows it all in a **Streamlit** dashboard. A separate worker scrapes
prices with **Selenium + BeautifulSoup** and emails you when a price reaches your target.

This is a rebuild of one of my project (originally Flask + TinyDB + requests). The rebuild
moves storage to MySQL, adds a real analytics layer, and uses Selenium because plain `requests`
calls are often blocked by Amazon.

## Features
- Add a product by link, set a target price and an alert email
- Scheduled price checks (separate worker process), history stored in MySQL
- **Analytics per product:** min / max / mean / median, volatility (std ÷ mean), % above the lowest
  price, % vs average, rolling average, biggest drops, daily summary table
- **Rule-based buy signal** (Buy / Good deal / Fair / Wait) — a heuristic on past prices, *not* a forecast
- **Charts:** price trend with rolling average and target line, price distribution, multi-product
  comparison indexed to 100
- **SQL analytics** using CTEs and window functions (`LAG`, `MIN() OVER`, `RANK`) — see `sql/analysis_queries.sql`
- Email alerts (once per new low, re-armed when the price goes back above target)
- Export any product's history as CSV

## Architecture
```
 Streamlit app (app.py) ──┐
                          ├──►  MySQL  (products, price_history)
 Worker (worker.py)  ─────┘        ▲
   Selenium → parsing.py (BeautifulSoup) → db.py
   └─ notifier.py (smtplib) on price ≤ target
 analytics.py: pandas + Matplotlib, used by the dashboard
```
The worker is a separate process because Streamlit re-runs the whole script on every interaction,
which makes background threads inside it unreliable.

## Tech stack
| Layer | Tool |
|---|---|
| Interface | Streamlit |
| Database | MySQL 8.0+ via SQLAlchemy + mysql-connector-python |
| Scraping | Selenium (headless Chrome) + BeautifulSoup |
| Analysis & charts | pandas, NumPy, Matplotlib |
| Alerts | smtplib (Gmail SMTP) |
| Config | python-dotenv |

## Setup
1. **Requirements:** Python 3.10+, MySQL 8.0+, Google Chrome installed.
2. Install dependencies:
   ```bash
   python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Create the database:
   ```bash
   mysql -u root -p < sql/schema.sql
   ```
4. Copy `.env.example` to `.env` and fill in your MySQL password and (optionally) a Gmail
   **App Password** for alerts.
5. Optional demo data (synthetic prices, labelled `[DEMO]`):
   ```bash
   python seed_demo.py
   ```
6. Run the dashboard:
   ```bash
   streamlit run app.py
   ```
7. Run the price checker (separate terminal):
   ```bash
   python worker.py --once        # a single cycle
   python worker.py --interval 60 # every 60 minutes
   ```

## How the analytics work
- **Volatility** = standard deviation ÷ mean × 100 (coefficient of variation).
- **Buy signal** (needs ≥ 5 checks): within 2% of the lowest price → *Buy*; ≥ 5% below the mean →
  *Good deal*; ≥ 5% above the mean → *Wait*; otherwise *Fair*.
- **Biggest drops** are computed in SQL (`LAG()` over a per-product window) on the dashboard and in
  pandas (`pct_change`) on the product page.

## Tests
```bash
pytest
```
Covers HTML/price parsing, URL cleaning, the analytics functions and the SQL layer (the SQL tests
run the same queries against a temporary SQLite database, so MySQL is not needed to run the tests).

## Limitations
- Amazon changes its page layout and uses bot detection. Selenium makes blocking less likely, but it
  can still show a CAPTCHA. The worker detects that, skips the product and logs a warning. The
  dashboard also lets you add a product or a price manually.
- Price selectors in `parsing.py` may need updating if Amazon changes its markup.
- Built and tested for amazon.in (₹); other regions need the currency symbol in `config.py` and may
  need parsing changes for different number formats.
- The buy signal only looks at past prices. It is not a prediction.
- Scraping may be against a site's terms of service. This project is for learning and personal use;
  keep request volumes low.

## Project structure
```
app.py            Streamlit dashboard
worker.py         scheduled price checker + alerts
scraper.py        Selenium browser wrapper
parsing.py        BeautifulSoup parsing, URL cleaning, CAPTCHA detection
analytics.py      pandas statistics + Matplotlib charts
db.py             all SQL (SQLAlchemy)
notifier.py       email alerts
seed_demo.py      synthetic demo data
sql/              schema.sql, analysis_queries.sql
tests/            pytest suite
```

## Screenshots

### Dashboard
![Dashboard](screenshots/Screenshot%202026-10-30%20202954.png)

### Product analysis
![Product analysis](screenshots/ss%20amazon%20tracker.pdf)

## Ideas for future work
- Price-drop forecasting (e.g. a simple time-series model) with proper backtesting
- Support for other stores
- Docker Compose for MySQL + app
