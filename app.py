"""Streamlit dashboard.   Run with:  streamlit run app.py"""
from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

import analytics
import config
import db
from parsing import ScrapeError, clean_url

CUR = config.CURRENCY
st.set_page_config(page_title="Amazon Price Tracker", page_icon="📉", layout="wide")


def show(fig) -> None:
    st.pyplot(fig)
    plt.close(fig)


def scrape_once(url: str) -> dict:
    """Open a browser, fetch one product, close it. Imported lazily so the app starts fast."""
    from scraper import AmazonScraper
    with AmazonScraper() as scraper:
        return scraper.fetch(url)


# ------------------------------------------------------------------ DB check
try:
    products = db.get_products()
except Exception as exc:  # wrong password, MySQL not running, schema missing...
    st.error("Could not connect to MySQL. Check your .env and that sql/schema.sql has been run.")
    st.code(str(exc))
    st.stop()

st.title("📉 Amazon Price Tracker")
st.caption("Selenium + BeautifulSoup scraping · MySQL storage · pandas / Matplotlib analytics")

# ------------------------------------------------------------------ sidebar: add product
with st.sidebar:
    st.header("Add a product")
    with st.form("add_product", clear_on_submit=True):
        url = st.text_input("Amazon product link")
        target = st.number_input(f"Target price ({CUR})", min_value=0.0, step=50.0,
                                 help="Set 0 for no target.")
        email = st.text_input("Email for alerts (optional)")
        manual = st.checkbox("Enter details manually (skip scraping)")
        m_title = st.text_input("Title (manual only)")
        m_price = st.number_input(f"Current price ({CUR}) (manual only)", min_value=0.0, step=50.0)
        submitted = st.form_submit_button("Start tracking")

    if submitted:
        try:
            clean = clean_url(url)
            if manual:
                if not m_title or m_price <= 0:
                    raise ValueError("Manual mode needs a title and a price.")
                data = {"title": m_title, "price": float(m_price)}
            else:
                with st.spinner("Opening Amazon in a headless browser..."):
                    data = scrape_once(clean)
            pid = db.add_product(clean, data["title"], target or None, email.strip() or None)
            db.add_price(pid, data["price"])
            st.success(f"Tracking: {data['title'][:60]} at {CUR}{data['price']:,.0f}")
            st.rerun()
        except (ValueError, ScrapeError) as exc:
            st.error(str(exc))
            st.info("If Amazon blocks the browser, tick 'Enter details manually' to add it anyway.")
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")

if products.empty:
    st.info("No products yet. Add one from the sidebar, or run `python seed_demo.py` for demo data.")
    st.stop()

titles = dict(zip(products["id"], products["title"]))
stats_table = db.latest_stats()
all_history = db.get_all_history()

tab_dash, tab_prod, tab_cmp, tab_manage = st.tabs(
    ["📊 Dashboard", "🔍 Product analysis", "📈 Compare", "⚙️ Manage"]
)

# ------------------------------------------------------------------ dashboard
with tab_dash:
    rows = []
    for _, r in stats_table.iterrows():
        hist = all_history[all_history["product_id"] == r["id"]]
        label, _ = analytics.buy_signal(analytics.summary_stats(hist))
        rows.append({
            "Product": r["title"], "Current": r["current_price"], "Lowest": r["min_price"],
            "Highest": r["max_price"], "Average": r["avg_price"], "Target": r["target_price"],
            "Checks": r["checks"], "Signal": label, "Active": bool(r["is_active"]),
        })
    overview = pd.DataFrame(rows)

    at_target = overview[(overview["Target"].notna()) & (overview["Current"] <= overview["Target"])]
    c1, c2, c3 = st.columns(3)
    c1.metric("Products tracked", len(overview))
    c2.metric("At or below target", len(at_target))
    c3.metric("Price checks stored", int(overview["Checks"].sum()))

    st.dataframe(
        overview, width="stretch", hide_index=True,
        column_config={c: st.column_config.NumberColumn(format=f"{CUR}%.0f")
                       for c in ("Current", "Lowest", "Highest", "Average", "Target")},
    )

    with st.expander("Biggest single-check price drops (SQL: CTE + LAG window function)"):
        try:
            st.dataframe(db.biggest_drops(), width="stretch", hide_index=True)
        except Exception as exc:
            st.warning(f"This query needs MySQL 8.0+. ({exc})")

# ------------------------------------------------------------------ product analysis
with tab_prod:
    ids = products["id"].tolist()
    pid = st.selectbox("Product", ids, format_func=lambda i: titles[i])
    prod = products[products["id"] == pid].iloc[0]
    hist = db.get_history(int(pid))

    st.markdown(f"[Open on Amazon]({prod['url']})")

    left, right = st.columns([3, 1])
    with right:
        if st.button("Check price now"):
            try:
                with st.spinner("Fetching..."):
                    data = scrape_once(prod["url"])
                db.add_price(int(pid), data["price"])
                st.rerun()
            except Exception as exc:
                st.error(f"Could not fetch: {exc}")
        with st.expander("Add a price manually"):
            manual_price = st.number_input(f"Price ({CUR})", min_value=0.0, step=50.0, key="mp")
            if st.button("Save price") and manual_price > 0:
                db.add_price(int(pid), float(manual_price))
                st.rerun()

    if hist.empty:
        st.info("No price history yet.")
    else:
        s = analytics.summary_stats(hist)
        label, reason = analytics.buy_signal(s)
        m = st.columns(5)
        m[0].metric("Current", f"{CUR}{s['current']:,.0f}", f"{s['total_change_pct']:+.1f}% since first check")
        m[1].metric("Lowest", f"{CUR}{s['min']:,.0f}")
        m[2].metric("Highest", f"{CUR}{s['max']:,.0f}")
        m[3].metric("Average", f"{CUR}{s['mean']:,.0f}")
        m[4].metric("Volatility", f"{s['volatility_pct']:.1f}%", help="Std. deviation as % of the mean")
        st.info(f"**Signal: {label}.** {reason}  \n"
                "_A simple rule on past prices, not a prediction._")

        target_val = float(prod["target_price"]) if pd.notna(prod["target_price"]) else None
        window = st.slider("Rolling average window (checks)", 2, 30, 7)
        show(analytics.plot_price_trend(hist, target_val, window, titles[pid][:70]))

        a, b = st.columns(2)
        with a:
            show(analytics.plot_distribution(hist))
        with b:
            st.subheader("Biggest drops")
            st.dataframe(analytics.biggest_drops(hist), hide_index=True, width="stretch")
            st.subheader("Daily summary")
            st.dataframe(analytics.daily_summary(hist).tail(14), hide_index=True,
                         width="stretch")

        st.download_button("Download history as CSV",
                           hist[["checked_at", "price"]].to_csv(index=False),
                           file_name=f"price_history_{pid}.csv", mime="text/csv")

# ------------------------------------------------------------------ compare
with tab_cmp:
    chosen = st.multiselect("Products to compare", products["title"].tolist(),
                            default=products["title"].tolist()[:4])
    subset = all_history[all_history["title"].isin(chosen)]
    if subset.empty:
        st.info("Pick at least one product with price history.")
    else:
        show(analytics.plot_comparison(subset))

# ------------------------------------------------------------------ manage
with tab_manage:
    pid_m = st.selectbox("Product to edit", products["id"].tolist(),
                         format_func=lambda i: titles[i], key="manage_select")
    row = products[products["id"] == pid_m].iloc[0]
    new_target = st.number_input(
        f"Target price ({CUR}, 0 = none)", min_value=0.0, step=50.0,
        value=float(row["target_price"]) if pd.notna(row["target_price"]) else 0.0)
    active = st.checkbox("Actively tracked (worker will check it)", value=bool(row["is_active"]))
    if st.button("Save changes"):
        db.update_product(int(pid_m), new_target or None, active)
        st.success("Saved.")
        st.rerun()

    st.divider()
    confirm = st.checkbox("I understand this deletes the product and its price history")
    if st.button("Delete product", disabled=not confirm):
        db.delete_product(int(pid_m))
        st.rerun()
