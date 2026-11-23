"""Price analytics with pandas / NumPy and Matplotlib charts.

All functions take a DataFrame with at least `checked_at` (datetime) and `price` (float).
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config

MIN_CHECKS_FOR_SIGNAL = 5


def prepare(df: pd.DataFrame, window: int = 7) -> pd.DataFrame:
    """Sort by time and add rolling average, % change and running minimum columns."""
    d = df.sort_values("checked_at").reset_index(drop=True).copy()
    d["rolling_avg"] = d["price"].rolling(window, min_periods=1).mean()
    d["pct_change"] = d["price"].pct_change() * 100
    d["running_min"] = d["price"].cummin()
    return d


def summary_stats(df: pd.DataFrame) -> dict:
    """Headline numbers for one product's price history."""
    if df.empty:
        return {}
    d = df.sort_values("checked_at")
    p = d["price"].astype(float)
    current, first = float(p.iloc[-1]), float(p.iloc[0])
    low, high, mean = float(p.min()), float(p.max()), float(p.mean())
    std = float(p.std(ddof=1)) if len(p) > 1 else 0.0
    return {
        "current": current,
        "min": low,
        "max": high,
        "mean": mean,
        "median": float(p.median()),
        "std": std,
        "volatility_pct": std / mean * 100 if mean else 0.0,   # coefficient of variation
        "pct_above_min": (current - low) / low * 100 if low else 0.0,
        "pct_vs_mean": (current - mean) / mean * 100 if mean else 0.0,
        "total_change_pct": (current - first) / first * 100 if first else 0.0,
        "checks": int(len(p)),
        "first_checked": d["checked_at"].iloc[0],
        "last_checked": d["checked_at"].iloc[-1],
    }


def buy_signal(stats: dict) -> tuple[str, str]:
    """Simple rule-based label + reason. A heuristic on past prices, NOT a forecast."""
    if not stats or stats["checks"] < MIN_CHECKS_FOR_SIGNAL:
        n = stats["checks"] if stats else 0
        return "Not enough data", f"Needs at least {MIN_CHECKS_FOR_SIGNAL} checks (has {n})."
    if stats["pct_above_min"] <= 2:
        return "Buy", "Within 2% of the lowest price seen so far."
    if stats["pct_vs_mean"] <= -5:
        return "Good deal", f"{abs(stats['pct_vs_mean']):.1f}% below the average price."
    if stats["pct_vs_mean"] >= 5:
        return "Wait", f"{stats['pct_vs_mean']:.1f}% above the average price."
    return "Fair", "Close to the average price."


def daily_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One row per calendar day: min / max / mean / last price and number of checks."""
    d = df.sort_values("checked_at").copy()
    d["date"] = d["checked_at"].dt.date
    out = d.groupby("date").agg(
        low=("price", "min"), high=("price", "max"), avg=("price", "mean"),
        last=("price", "last"), checks=("price", "count"),
    )
    return out.round(2).reset_index()


def biggest_drops(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Largest check-to-check drops for one product."""
    d = prepare(df)
    drops = d[d["pct_change"] < 0].nsmallest(n, "pct_change")
    return drops[["checked_at", "price", "pct_change"]].reset_index(drop=True)


def shorten(text: str, n: int = 45) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


# ---------------------------------------------------------------- charts
def plot_price_trend(df: pd.DataFrame, target: float | None = None,
                     window: int = 7, title: str | None = None):
    d = prepare(df, window)
    cur = config.CURRENCY
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(d["checked_at"], d["price"], marker="o", ms=3, lw=1.4, label="Price")
    ax.plot(d["checked_at"], d["rolling_avg"], ls="--", lw=1.6, label=f"{window}-check average")

    i_min, i_max = d["price"].idxmin(), d["price"].idxmax()
    ax.scatter(d["checked_at"][i_min], d["price"][i_min], color="green", zorder=5,
               label=f"Lowest ({cur}{d['price'][i_min]:,.0f})")
    ax.scatter(d["checked_at"][i_max], d["price"][i_max], color="red", zorder=5,
               label=f"Highest ({cur}{d['price'][i_max]:,.0f})")
    if target:
        ax.axhline(target, color="orange", ls=":", lw=1.8, label=f"Target ({cur}{target:,.0f})")

    ax.set_title(title or "Price history")
    ax.set_ylabel(f"Price ({cur})")
    ax.grid(alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def plot_distribution(df: pd.DataFrame, title: str | None = None):
    """Histogram of observed prices with the current price marked."""
    cur = config.CURRENCY
    prices = df.sort_values("checked_at")["price"]
    fig, ax = plt.subplots(figsize=(6, 3.8))
    bins = max(5, min(20, int(np.sqrt(len(prices)) * 1.5)))
    ax.hist(prices, bins=bins, edgecolor="white")
    ax.axvline(prices.iloc[-1], color="red", lw=2, label=f"Current ({cur}{prices.iloc[-1]:,.0f})")
    ax.axvline(prices.mean(), color="black", ls="--", lw=1.5, label=f"Mean ({cur}{prices.mean():,.0f})")
    ax.set_title(title or "Price distribution")
    ax.set_xlabel(f"Price ({cur})")
    ax.set_ylabel("Number of checks")
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


def plot_comparison(history: pd.DataFrame):
    """Compare products on one chart by indexing each to 100 at its first check."""
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for title, grp in history.groupby("title"):
        g = grp.sort_values("checked_at")
        first = g["price"].iloc[0]
        if first:
            ax.plot(g["checked_at"], g["price"] / first * 100, lw=1.6, label=shorten(title))
    ax.axhline(100, color="grey", lw=0.8)
    ax.set_title("Relative price movement (first check = 100)")
    ax.set_ylabel("Price index")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig
