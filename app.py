# app.py
import streamlit as st
from datetime import datetime, date
import base64
import os
from PIL import Image
import pandas as pd
import io

from db import init_db, add_expense, get_expenses, clear_all
from analysis import analyze_spending, parse_nl_expense
from charts import pie_chart, bar_chart, line_chart

BASE_DIR = os.path.dirname(__file__)
AWARE_DIR = os.path.join(BASE_DIR, "awareness")

st.set_page_config(page_title="Expense Tracker", layout="wide", initial_sidebar_state="expanded")

# ----------------- helpers -----------------
def set_background(image_path: str):
    """Set a full-page background using CSS and base64 image data."""
    if not os.path.exists(image_path):
        return
    with open(image_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    css = f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{b64}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    .panel {{
        background: rgba(255,255,255,0.85);
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def load_image(path, width=None):
    if not os.path.exists(path):
        return None
    img = Image.open(path)
    if width:
        ratio = width / img.width
        img = img.resize((width, int(img.height * ratio)), Image.LANCZOS)
    return img

# Set default background permanently
init_db()
default_bg = os.path.join(AWARE_DIR, "default.png")
set_background(default_bg)


def df_from_rows(rows):
    if not rows:
        return pd.DataFrame(columns=["id","amount","category","date"])
    df = pd.DataFrame(rows, columns=["id","amount","category","date"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], format="mixed", errors="coerce")
    df["category"] = df["category"].str.lower().str.strip()
    return df


# ----------------- TIMEFRAME FILTER LOGIC -----------------
def filter_by_timeframe(df, timeframe):
    now = pd.Timestamp.now()
    if df.empty:
        return df

    if timeframe == "This Month":
        start = now.replace(day=1)
        return df[df["date"] >= start]

    elif timeframe == "Last Month":
        prev = now - pd.DateOffset(months=1)
        start = prev.replace(day=1)
        end = prev.replace(day=1) + pd.offsets.MonthEnd(0)
        return df[(df["date"] >= start) & (df["date"] <= end)]

    elif timeframe == "Last 3 Months":
        start = (now - pd.DateOffset(months=3)).replace(day=1)
        return df[df["date"] >= start]

    elif timeframe == "This Year":
        start = now.replace(month=1, day=1)
        return df[df["date"] >= start]

    elif timeframe == "All Time":
        return df

    return df





# ----------------- Sidebar -----------------
st.sidebar.title("Expense Tracker")
st.sidebar.markdown("---")

# Theme toggle
if "theme_dark" not in st.session_state:
    st.session_state.theme_dark = False

st.sidebar.checkbox("Dark mode", value=st.session_state.theme_dark, key="theme_dark")

st.sidebar.markdown("---")
st.sidebar.image(os.path.join(AWARE_DIR, "default.png"), use_container_width=True)

st.sidebar.subheader("Actions")
if st.sidebar.button("Refresh Data"):
    st.rerun()
if st.sidebar.button("Clear all data (danger)"):
    clear_all()
    st.success("All data cleared.")
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("Made with ❤️ by Manas")



# ----------------- Main Layout -----------------
panel_style = "<div class='panel' style='{}'>"
bg_overlay = "background: rgba(0,0,0,0.45);" if st.session_state.theme_dark else ""
st.markdown(panel_style.format("padding:8px; "+bg_overlay), unsafe_allow_html=True)

col1, col2 = st.columns([3,2])

# -------------------------------------------------------------
# LEFT SIDE — ADD EXPENSE + TABLE
# -------------------------------------------------------------
with col1:
    st.subheader("Add Expense")

    st.markdown("**Quick add (e.g. `200 food today`)**")
    nl_input = st.text_input("Quick add (optional)", placeholder="e.g. 200 food today")
    if st.button("Parse & Add from text"):
        parsed = parse_nl_expense(nl_input)
        if parsed:
            amt, cat, dt = parsed
            add_expense(float(amt), cat.lower(), dt.isoformat())
            st.success(f"Added ₹{amt} → {cat} on {dt.date()}")
            st.rerun()
        else:
            st.error("Could not parse text. Try: 200 food today")

    with st.form("add_form", clear_on_submit=True):
        amt = st.number_input("Amount (₹)", min_value=0.0, format="%.2f")
        cat = st.selectbox("Category", ["Food", "Shopping", "Travel", "Bills"])
        date_input = st.date_input("Date", value=datetime.now().date())
        submitted = st.form_submit_button("Save")

        if submitted:
            if amt > 0:
                add_expense(float(amt), cat.lower(), date_input.isoformat())
                st.success("Expense saved.")
                st.rerun()
            else:
                st.error("Enter valid amount.")

    st.markdown("### Expense Table")

    # Load + filter
    rows = get_expenses()
    df = df_from_rows(rows)

    # Timeframe chosen from right-side section
    tf = st.session_state.get("timeframe", "This Month")
    df_filtered = filter_by_timeframe(df, tf)

    if not df_filtered.empty:
        st.dataframe(
            df_filtered.style.format({"amount": "{:.2f}"}),
            use_container_width=True
        )
    else:
        st.info("No data in selected timeframe.")

    # CSV IMPORT/EXPORT
    st.markdown("---")
    st.subheader("Import / Export")

    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded:
        try:
            up = pd.read_csv(uploaded)
            for _, r in up.iterrows():
                add_expense(float(r["amount"]), str(r["category"]).lower(), str(r["date"]))
            st.success("Imported successfully!")
            st.rerun()
        except Exception as e:
            st.error("Import failed: " + str(e))

    if not df_filtered.empty:
        csv_data = df_filtered.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV (filtered)",
                           data=csv_data,
                           file_name="expenses_filtered.csv",
                           mime="text/csv")


# -------------------------------------------------------------
# RIGHT SIDE — SMART SUGGESTIONS + KPI
# -------------------------------------------------------------
with col2:
    st.subheader("Smart Suggestions & Summary")

    tf = st.selectbox("Timeframe",
                      ["This Month", "Last Month", "Last 3 Months", "This Year", "All Time"],
                      key="timeframe")

    # Apply filter again because user may change timeframe now
    df_filtered = filter_by_timeframe(df, tf)

    analysis = analyze_spending(
        df_filtered.to_records(index=False),
        timeframe=tf
    )

    # KPI METRICS
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Spent", f"₹{analysis['total']:.2f}")
    k2.metric("Top Category", (analysis["top_category"] or "—").title())
    k3.metric("Entries", analysis["count"])

    st.write(analysis["suggestion"])

    img_path = analysis.get("image_path", default_bg)
    img = load_image(img_path, width=360)
    if img:
        st.image(img, use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)


# ----------------- Charts -----------------
st.markdown("<div class='panel' style='margin-top:16px;'>", unsafe_allow_html=True)
c1, c2 = st.columns(2)

with c1:
    st.subheader("Category Distribution")
    fig = pie_chart(df_filtered.to_records(index=False))
    st.pyplot(fig)

with c2:
    st.subheader("Recent spending (90 days)")
    fig2 = bar_chart(df_filtered.to_records(index=False))
    st.pyplot(fig2)

# LINE CHART
st.markdown("<div class='panel' style='margin-top:16px;'>", unsafe_allow_html=True)
st.subheader("Monthly Trend (Last 12 months)")
fig3 = line_chart(df_filtered.to_records(index=False))
st.pyplot(fig3)
st.markdown("</div>", unsafe_allow_html=True)
