import matplotlib.pyplot as plt
import pandas as pd

import analytics


def make_df(prices):
    return pd.DataFrame({
        "checked_at": pd.date_range("2026-01-01", periods=len(prices), freq="12h"),
        "price": prices, "title": "Item", "product_id": 1,
    })


def test_summary_stats_basic():
    s = analytics.summary_stats(make_df([100, 120, 80, 100]))
    assert s["min"] == 80 and s["max"] == 120 and s["current"] == 100
    assert s["mean"] == 100 and s["checks"] == 4
    assert round(s["pct_above_min"], 1) == 25.0


def test_single_row_has_zero_volatility():
    assert analytics.summary_stats(make_df([500]))["volatility_pct"] == 0.0


def test_buy_signal_branches():
    assert analytics.buy_signal(analytics.summary_stats(make_df([100, 110])))[0] == "Not enough data"
    assert analytics.buy_signal(analytics.summary_stats(make_df([120, 110, 115, 112, 100])))[0] == "Buy"
    assert analytics.buy_signal(analytics.summary_stats(make_df([100, 100, 100, 100, 130])))[0] == "Wait"
    assert analytics.buy_signal(analytics.summary_stats(make_df([100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 94])))[0] in ("Good deal", "Buy")
    assert analytics.buy_signal(analytics.summary_stats(make_df([100, 90, 110, 100, 102])))[0] == "Fair"


def test_prepare_and_drops():
    d = analytics.prepare(make_df([100, 90, 95, 80]), window=2)
    assert d["running_min"].tolist() == [100, 90, 90, 80]
    drops = analytics.biggest_drops(make_df([100, 90, 95, 80]), n=1)
    assert drops["price"].iloc[0] == 80


def test_daily_summary_groups_by_day():
    out = analytics.daily_summary(make_df([100, 90, 95, 80]))
    assert len(out) == 2 and out["checks"].tolist() == [2, 2]


def test_charts_return_figures():
    df = make_df([100, 90, 95, 80, 85, 99])
    for fig in (analytics.plot_price_trend(df, target=85), analytics.plot_distribution(df),
                analytics.plot_comparison(df)):
        assert isinstance(fig, plt.Figure)
        plt.close(fig)
