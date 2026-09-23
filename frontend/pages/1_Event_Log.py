"""
pages/1_Event_Log.py
Streamlit live dashboard - Page 2: Event Log & Summary.

Shows the "evidence" side of the project: aggregate counts and a
filterable history table. Two stats matter most for your review:
- "False-Positives Suppressed" -> evidences the intent-aware masking claim
- "Crash False Alarms Rejected" -> evidences the two-stage confirmation claim
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

if not is_backend_reachable():
    st.error(
        "⚠️ Cannot reach the backend at http://localhost:5000. "
        "Make sure `python app.py` is running in the backend folder."
    )
    st.stop()

# ---------- Summary metrics ----------

stats = get_stats()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Readings", stats.get("total_readings", 0))
col2.metric("Crashes Confirmed", stats.get("total_crashes", 0))
col3.metric("Alerts Triggered", stats.get("total_alerts", 0))
col4.metric("False-Positives Suppressed", stats.get("total_suppressed", 0))
col5.metric("Crash False Alarms Rejected", stats.get("total_false_alarms", 0))

st.caption(
    "\"False-Positives Suppressed\" = alerts prevented by intent-aware head-turn masking. "
    "\"Crash False Alarms Rejected\" = impact spikes (e.g. potholes) correctly ruled out by "
    "the two-stage no-motion confirmation check, rather than triggering a false emergency."
)

st.divider()

# ---------- Event history table ----------

st.subheader("Event History")

history = get_history(limit=100)

if not history:
    st.info("No events logged yet. Trigger some from the Live Dashboard page or start the simulator.")
    st.stop()

df = pd.DataFrame(history)

severity_emoji = {"none": "🟩 none", "caution": "🟧 caution", "high": "🟥 high"}
df["left_severity"] = df["left_severity"].map(severity_emoji).fillna(df["left_severity"])
df["right_severity"] = df["right_severity"].map(severity_emoji).fillna(df["right_severity"])
df["head_turn_active"] = df["head_turn_active"].map({1: "Yes", 0: "No"})
df["crash_flag"] = df["crash_flag"].map({1: "Yes", 0: "No"})

crash_stage_emoji = {
    "none": "⬜ none",
    "impact_detected": "🟠 confirming",
    "confirmed": "🟥 confirmed",
    "false_alarm": "🟦 false alarm",
}
df["crash_stage"] = df["crash_stage"].map(crash_stage_emoji).fillna(df["crash_stage"])

event_types = sorted(df["event_type"].unique().tolist())
selected_types = st.multiselect(
    "Filter by event type",
    options=event_types,
    default=event_types
)

filtered_df = df[df["event_type"].isin(selected_types)]

display_columns = [
    "timestamp", "event_type", "active_alert",
    "left_severity", "left_ttc", "right_severity", "right_ttc",
    "crash_stage", "head_turn_active", "notes"
]

st.dataframe(
    filtered_df[display_columns],
    use_container_width=True,
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
