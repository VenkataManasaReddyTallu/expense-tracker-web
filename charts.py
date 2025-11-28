# charts.py
from typing import List, Tuple
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams.update({'figure.max_open_warning': 0})


# -------------------- Convert rows to clean DataFrame --------------------
def rows_to_df(rows):
    # FIX for numpy structured arrays: never use "if not rows"
    if rows is None or len(rows) == 0:
        return pd.DataFrame(columns=["id", "amount", "category", "date"])

    df = pd.DataFrame(rows, columns=["id", "amount", "category", "date"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["category"] = df["category"].astype(str).str.lower().str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    return df


# -------------------- PIE Chart --------------------
def pie_chart(rows):
    df = rows_to_df(rows)
    fig, ax = plt.subplots(figsize=(4, 4))

    if df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.axis("off")
        return fig

    agg = df.groupby("category")["amount"].sum()

    if agg.sum() == 0:
        ax.text(0.5, 0.5, "No spending", ha="center", va="center")
        ax.axis("off")
        return fig

    ax.pie(
        agg.values,
        labels=[c.title() for c in agg.index],
        autopct="%1.1f%%",
        startangle=140,
    )
    ax.set_title("Spending by Category")
    return fig


# -------------------- BAR Chart (Last 90 days) --------------------
def bar_chart(rows):
    df = rows_to_df(rows)
    fig, ax = plt.subplots(figsize=(6, 3))

    if df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.axis("off")
        return fig

    cutoff = pd.Timestamp.now() - pd.Timedelta(days=90)
    df = df[df["date"] >= cutoff]

    if df.empty:
        ax.text(0.5, 0.5, "No recent spending", ha="center", va="center")
        ax.axis("off")
        return fig

    agg = df.groupby("category")["amount"].sum().sort_values(ascending=False)

    agg.plot(kind="bar", ax=ax)
    ax.set_ylabel("Amount")
    ax.set_title("Spending in Last 90 Days")
    plt.tight_layout()
    return fig


# -------------------- LINE Chart (Monthly Trend — 12 months) --------------------
def line_chart(rows):
    df = rows_to_df(rows)
    fig, ax = plt.subplots(figsize=(8, 3))

    if df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.axis("off")
        return fig

    df["month"] = df["date"].dt.to_period("M")
    last12 = (pd.Timestamp.now() - pd.DateOffset(months=11)).to_period("M")
    df = df[df["month"] >= last12]

    agg = df.groupby("month")["amount"].sum()

    # Ensure all months filled
    months = pd.period_range(last12, pd.Timestamp.now().to_period("M"), freq="M")
    agg = agg.reindex(months, fill_value=0)

    ax.plot(agg.index.astype(str), agg.values, marker="o")
    ax.set_title("Monthly Spending (Last 12 Months)")
    ax.set_ylabel("Amount")
    ax.set_xticklabels([str(m) for m in agg.index], rotation=45, ha="right")
    plt.tight_layout()
    return fig
