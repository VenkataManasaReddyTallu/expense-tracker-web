# analysis.py
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from datetime import datetime
import os
import re

BASE_DIR = os.path.dirname(__file__)
AWARENESS_DIR = os.path.join(BASE_DIR, "awareness")


# -------------------- Load Category Images --------------------
def load_awareness_filename(category: str) -> str:
    mapping = {
        "food": "food.png",
        "shopping": "shopping.png",
        "travel": "travel.png",
        "bills": "bills.png",
    }
    fname = mapping.get(category.lower(), "default.png")
    path = os.path.join(AWARENESS_DIR, fname)
    return path if os.path.exists(path) else os.path.join(AWARENESS_DIR, "default.png")


# -------------------- Convert DB rows -> DataFrame --------------------
def rows_to_df(rows: List[tuple]) -> pd.DataFrame:
    if rows is None or len(rows) == 0:
        return pd.DataFrame(columns=["id", "amount", "category", "date"])

    df = pd.DataFrame(rows, columns=["id", "amount", "category", "date"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["category"] = df["category"].fillna("").str.lower().str.strip()

    return df


# -------------------- Analyze Spending --------------------
def analyze_spending(rows: List[tuple], timeframe: str = "This Month") -> Dict[str, Any]:
    df = rows_to_df(rows)

    result = {
        "suggestion": "No expenses yet.",
        "top_category": None,
        "percent_of_total": 0.0,
        "total": 0.0,
        "count": 0,
        "image_path": os.path.join(AWARENESS_DIR, "default.png"),
    }

    if df.empty:
        return result

    # Total & count
    total = df["amount"].sum()
    result["total"] = float(total)
    result["count"] = int(df.shape[0])

    if total <= 0:
        result["suggestion"] = "No expenses added in this timeframe."
        return result

    # Category totals
    cat_totals = df.groupby("category")["amount"].sum().sort_values(ascending=False)

    top_cat = cat_totals.index[0]
    top_amt = float(cat_totals.iloc[0])
    percent = (top_amt / total) * 100

    result["top_category"] = top_cat
    result["percent_of_total"] = percent
    result["image_path"] = load_awareness_filename(top_cat)

    # Build suggestions
    lines = []

    if percent >= 40:
        lines.append(f"🚨 You spent {percent:.1f}% on **{top_cat.title()}**.")
    elif percent >= 25:
        lines.append(f"⚠️ {top_cat.title()} makes up {percent:.1f}% of your spending.")
    else:
        lines.append("✅ Your spending is well balanced.")

    # Category-specific tips
    tips = {
        "food": "Try reducing takeout and cook at home more often.",
        "shopping": "Use a wishlist and buy only after 48 hours.",
        "travel": "Look for discount deals or plan trips off-season.",
        "bills": "Review subscriptions and remove unused services.",
    }
    lines.append("💡 Tip: " + tips.get(top_cat, "Track recurring expenses."))

    result["suggestion"] = "\n".join(lines)

    return result


# -------------------- Natural Language Parsing --------------------
def parse_nl_expense(text: str) -> Optional[Tuple[float, str, datetime]]:
    if not text or not text.strip():
        return None

    text = text.lower().strip()

    # Amount extraction
    amount_match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not amount_match:
        return None
    amount = float(amount_match.group(1))

    # Category detection
    categories = ["food", "shopping", "travel", "bills"]
    cat = None
    for c in categories:
        if c in text:
            cat = c
            break

    if not cat:
        return None  # avoid wrong category entries

    # Date detection
    if "today" in text:
        dt = datetime.now()
    elif "yesterday" in text:
        dt = datetime.now() - pd.Timedelta(days=1)
    else:
        # Handle exact date format
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        if date_match:
            try:
                dt = datetime.fromisoformat(date_match.group(1))
            except:
                dt = datetime.now()
        else:
            dt = datetime.now()

    return (amount, cat, dt)
