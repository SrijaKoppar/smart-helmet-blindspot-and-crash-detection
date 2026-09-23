"""
pages/1_Event_Log.py
Streamlit live dashboard - Page 2: Event Log & Summary.

Shows the "evidence" side of the project: aggregate counts and a
filterable history table, most importantly the count of alerts
suppressed by intent-aware head-turn masking - the strongest data
point for the project's false-positive-reduction claim.
"""

import streamlit as st
import pandas as pd
from api_client import get_history, get_stats, is_backend_reachable

st.set_page_config(
    page_title="Smart Helmet — Event Log",
    page_icon="📋",
    layout="wide"
)

st.title("📋 Event Log & Summary")

# ---------- Backend reachability check ----------

if not is_backend_reachable():
    st.error(
        "⚠️ Cannot reach the backend at http://localhost:5000. "
        "Make sure `python app.py` is running in the backend folder."
    )
    st.stop()

# ---------- Summary metrics ----------

stats = get_stats()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Readings", stats.get("total_readings", 0))
col2.metric("Crashes Detected", stats.get("total_crashes", 0))
col3.metric("Alerts Triggered", stats.get("total_alerts", 0))
col4.metric("False-Positives Suppressed", stats.get("total_suppressed", 0))

st.caption(
    "\"False-Positives Suppressed\" counts readings where intent-aware "
    "head-turn masking prevented an alert during a voluntary shoulder check."
)

st.divider()

# ---------- Event history table ----------

st.subheader("Event History")

history = get_history(limit=100)

if not history:
    st.info("No events logged yet. Trigger some from the Live Dashboard page or start the simulator.")
    st.stop()

df = pd.DataFrame(history)

# Friendly severity display with color-coded emoji, kept consistent with Page 1
severity_emoji = {"none": "🟩 none", "caution": "🟧 caution", "high": "🟥 high"}
df["left_severity"] = df["left_severity"].map(severity_emoji).fillna(df["left_severity"])
df["right_severity"] = df["right_severity"].map(severity_emoji).fillna(df["right_severity"])
df["head_turn_active"] = df["head_turn_active"].map({1: "Yes", 0: "No"})
df["crash_flag"] = df["crash_flag"].map({1: "Yes", 0: "No"})

# ---------- Filter ----------

event_types = sorted(df["event_type"].unique().tolist())
selected_types = st.multiselect(
    "Filter by event type",
    options=event_types,
    default=event_types
)

filtered_df = df[df["event_type"].isin(selected_types)]

display_columns = [
    "timestamp", "event_type", "active_alert",
    "left_severity", "right_severity",
    "head_turn_active", "crash_flag", "notes"
]

st.dataframe(
    filtered_df[display_columns],
    width='stretch',
    hide_index=True
)

st.divider()

# ---------- Alert type summary chart ----------

st.subheader("Alert Counts by Type")

alert_counts = df[df["active_alert"] != "none"]["active_alert"].value_counts()

if not alert_counts.empty:
    st.bar_chart(alert_counts)
else:
    st.caption("No alerts triggered yet in the logged history.")
