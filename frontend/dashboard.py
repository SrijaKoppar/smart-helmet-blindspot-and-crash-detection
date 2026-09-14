"""
dashboard.py
Streamlit live dashboard - Page 1.

Phase 3 scope (this file):
- Status banner reflecting current arbitration state
- Sensor metric cards (left/right distance, head-turn status)
- Auto-refresh so the page updates without manual reload

Phase 4 will add: live trend chart, arbitration priority indicator,
and the "Simulate Left Threat / Crash / Head-Turn" demo buttons.
"""

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from api_client import get_latest, is_backend_reachable

st.set_page_config(
    page_title="Smart Helmet Dashboard",
    page_icon="🪖",
    layout="wide"
)

# Auto-refresh the whole page every 1.5 seconds
st_autorefresh(interval=1500, key="live_refresh")

st.title("🪖 Smart Helmet — Live Dashboard")

# ---------- Backend reachability check ----------

if not is_backend_reachable():
    st.error(
        "⚠️ Cannot reach the backend at http://localhost:5000. "
        "Make sure `python app.py` is running in the backend folder."
    )
    st.stop()

# ---------- Fetch latest reading ----------

latest = get_latest()

if latest is None:
    st.info(
        "No readings yet. Start the simulator with `python simulate_esp32.py` "
        "in the backend folder, or wait for real helmet data."
    )
    st.stop()

# ---------- Status banner ----------

active_alert = latest.get("active_alert", "none")
crash_flag = latest.get("crash_flag", 0)

if crash_flag:
    st.error("🚨 **CRASH DETECTED — Emergency response triggered**")
elif active_alert == "blindspot_left":
    st.warning("⚠️ **Blind-Spot Alert — Vehicle approaching from LEFT**")
elif active_alert == "blindspot_right":
    st.warning("⚠️ **Blind-Spot Alert — Vehicle approaching from RIGHT**")
else:
    st.success("✅ **Monitoring — No active hazards**")

st.caption(f"Last updated: {latest.get('timestamp', 'unknown')}")

# ---------- Sensor metric cards ----------

col1, col2, col3 = st.columns(3)

with col1:
    left_distance = latest.get("left_distance")
    st.metric(
        label="Left Distance",
        value=f"{left_distance:.1f} cm" if left_distance is not None else "—",
        delta=latest.get("left_severity", "none").capitalize()
    )

with col2:
    right_distance = latest.get("right_distance")
    st.metric(
        label="Right Distance",
        value=f"{right_distance:.1f} cm" if right_distance is not None else "—",
        delta=latest.get("right_severity", "none").capitalize()
    )

with col3:
    head_turn = "Yes" if latest.get("head_turn_active") else "No"
    st.metric(
        label="Head-Turn Detected",
        value=head_turn,
        delta="Alerts suppressed" if latest.get("head_turn_active") else "Normal"
    )
