"""
dashboard.py
Streamlit live dashboard - Page 1.

Phase 3: status banner, sensor metric cards, auto-refresh.
Phase 4 (this update) adds:
- Live trend chart of left/right distance over recent readings
- Arbitration priority indicator (shows which hazard is "winning")
- Demo buttons to simulate Left/Right Threat, Crash, and Head-Turn -
  lets you reliably demo the arbitration logic without real hardware.
"""

import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from api_client import get_latest, get_history, is_backend_reachable, post_simulate

st.set_page_config(
    page_title="Smart Helmet Dashboard",
    page_icon="🪖",
    layout="wide"
)

with st.sidebar:
    st.markdown("### 🪖 Smart Helmet")
    st.caption("Adaptive Blind-Spot & Crash Alert Arbitration")
    st.divider()
    st.caption("Use the pages above to switch between the Live Dashboard and the Event Log.")

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

st.divider()

# ---------- Arbitration priority indicator ----------

st.subheader("Arbitration State")
st.caption("Shows which hazard is currently 'winning' the priority arbitration.")

arb_col1, arb_col2 = st.columns(2)

with arb_col1:
    if crash_flag:
        st.markdown("### 🟥 CRASH — Priority 1")
        st.caption("**ACTIVE** — overrides all other alerts")
    else:
        st.markdown("### ⬜ Crash — Priority 1")
        st.caption("Idle")

with arb_col2:
    if not crash_flag and active_alert in ("blindspot_left", "blindspot_right"):
        side = "LEFT" if active_alert == "blindspot_left" else "RIGHT"
        st.markdown(f"### 🟧 BLIND-SPOT {side} — Priority 2")
        st.caption("**ACTIVE** — directional haptic firing")
    elif latest.get("head_turn_active"):
        st.markdown("### 🟦 BLIND-SPOT — Priority 2")
        st.caption("**SUPPRESSED** — rider is intentionally head-turning")
    else:
        st.markdown("### ⬜ Blind-Spot — Priority 2")
        st.caption("Idle")

st.divider()

# ---------- Live trend chart ----------

st.subheader("Recent Distance Trend")

history = get_history(limit=30)

if history:
    df = pd.DataFrame(history)
    df = df.iloc[::-1].reset_index(drop=True)  # oldest -> newest, left to right
    chart_df = df[["left_distance", "right_distance"]].rename(
        columns={"left_distance": "Left (cm)", "right_distance": "Right (cm)"}
    )
    st.line_chart(chart_df)
else:
    st.caption("Not enough history yet to plot a trend.")

st.divider()

# ---------- Demo simulation controls ----------

st.subheader("Demo Controls")
st.caption("Use these to reliably trigger scenarios for a live demo, without needing real hardware.")

sim_col1, sim_col2, sim_col3, sim_col4 = st.columns(4)

with sim_col1:
    if st.button("⬅️ Simulate Left Threat", use_container_width=True):
        post_simulate("left_threat")
        st.rerun()

with sim_col2:
    if st.button("➡️ Simulate Right Threat", use_container_width=True):
        post_simulate("right_threat")
        st.rerun()

with sim_col3:
    if st.button("🚨 Simulate Crash", use_container_width=True):
        post_simulate("crash")
        st.rerun()

with sim_col4:
    if st.button("🔄 Simulate Head-Turn", use_container_width=True):
        post_simulate("head_turn")
        st.rerun()