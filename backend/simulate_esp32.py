"""
simulate_esp32.py
Mimics the ESP32 helmet sending periodic sensor readings to the Flask
backend, so the dashboard can be built and tested before hardware is
ready. Run this in a separate terminal, alongside app.py.

This version mirrors the actual planned firmware logic more closely:
- Severity is derived from TTC (time-to-collision), not raw distance
- Crash detection is two-stage: an impact spike first logs
  'impact_detected', then a short no-motion check resolves it to
  either 'confirmed' or 'false_alarm' (e.g. a pothole)

Usage:
    python simulate_esp32.py
    (Ctrl+C to stop)
"""

import requests
import random
import time

SERVER_URL = "http://localhost:5000/api/ingest"
INTERVAL_SECONDS = 1.5

# Track previous distances to derive a closing speed (cm/s), same
# calculation the firmware will do between consecutive ultrasonic reads
prev_left_distance = None
prev_right_distance = None


def compute_ttc(prev_distance, current_distance, interval_s=INTERVAL_SECONDS):
    """
    Returns (severity, ttc_seconds).
    TTC = distance / closing_speed, only if the object is actually closing.
    Mirrors the firmware's planned rate-of-closure calculation rather
    than a static distance threshold.
    """
    if prev_distance is None or current_distance is None:
        return "none", None

    closing_speed = (prev_distance - current_distance) / interval_s  # cm/s
    if closing_speed <= 5:  # not meaningfully closing (or moving away)
        return "none", None

    ttc = current_distance / closing_speed  # seconds

    if ttc < 1.5:
        return "high", round(ttc, 2)
    elif ttc < 4.0:
        return "caution", round(ttc, 2)
    return "none", round(ttc, 2)


def decide_active_alert(left_sev, right_sev, crash_flag, head_turn_active):
    """Priority arbitration: crash > blind-spot, and head-turn suppresses
    whichever side it applies to."""
    if crash_flag:
        return "crash"
    if head_turn_active:
        return "none"  # suppressed
    if left_sev == "high":
        return "blindspot_left"
    if right_sev == "high":
        return "blindspot_right"
    if left_sev == "caution":
        return "blindspot_left"
    if right_sev == "caution":
        return "blindspot_right"
    return "none"


def send(payload):
    try:
        response = requests.post(SERVER_URL, json=payload, timeout=3)
        if response.status_code == 201:
            print(f"Sent: {payload['notes']}")
        else:
            print(f"Server returned {response.status_code}: {response.text}")
    except requests.exceptions.ConnectionError:
        print("Could not reach Flask server - is app.py running?")


def generate_sensor_reading():
    """Generates one plausible reading using TTC-based severity."""
    global prev_left_distance, prev_right_distance

    left_distance = round(random.uniform(20, 400), 1)
    right_distance = round(random.uniform(20, 400), 1)

    left_severity, left_ttc = compute_ttc(prev_left_distance, left_distance)
    right_severity, right_ttc = compute_ttc(prev_right_distance, right_distance)

    prev_left_distance = left_distance
    prev_right_distance = right_distance

    head_turn_active = 1 if random.random() < 0.08 else 0
    active_alert = decide_active_alert(left_severity, right_severity, 0, head_turn_active)

    note_parts = []
    if left_severity != "none":
        note_parts.append(f"L closing, TTC={left_ttc}s ({left_severity})")
    if right_severity != "none":
        note_parts.append(f"R closing, TTC={right_ttc}s ({right_severity})")
    notes = "; ".join(note_parts) if note_parts else "Routine monitoring"

    return {
        "left_distance": left_distance,
        "right_distance": right_distance,
        "left_severity": left_severity,
        "right_severity": right_severity,
        "left_ttc": left_ttc,
        "right_ttc": right_ttc,
        "head_turn_active": head_turn_active,
        "crash_flag": 0,
        "crash_stage": "none",
        "active_alert": active_alert,
        "event_type": "sensor_update",
        "notes": notes
    }


def maybe_trigger_crash_sequence():
    """Occasionally simulates a two-stage crash event: impact detected,
    then resolved as either confirmed or a false alarm a moment later."""
    if random.random() >= 0.015:  # ~1.5% chance per loop iteration
        return

    send({
        "left_distance": None, "right_distance": None,
        "left_severity": "none", "right_severity": "none",
        "left_ttc": None, "right_ttc": None,
        "head_turn_active": 0, "crash_flag": 0, "crash_stage": "impact_detected",
        "active_alert": "crash", "event_type": "sensor_update",
        "notes": "Impact spike detected - confirming over next window..."
    })
    time.sleep(1.0)  # mimics the firmware's short no-motion confirmation window

    if random.random() < 0.6:  # most impacts in this demo resolve as real crashes
        send({
            "left_distance": None, "right_distance": None,
            "left_severity": "none", "right_severity": "none",
            "left_ttc": None, "right_ttc": None,
            "head_turn_active": 0, "crash_flag": 1, "crash_stage": "confirmed",
            "active_alert": "crash", "event_type": "crash",
            "notes": "No motion after impact - crash confirmed"
        })
    else:
        send({
            "left_distance": None, "right_distance": None,
            "left_severity": "none", "right_severity": "none",
            "left_ttc": None, "right_ttc": None,
            "head_turn_active": 0, "crash_flag": 0, "crash_stage": "false_alarm",
            "active_alert": "none", "event_type": "sensor_update",
            "notes": "Motion resumed (pothole) - false alarm rejected"
        })


def run():
    print(f"[simulate_esp32.py] Sending TTC-based readings to {SERVER_URL} every {INTERVAL_SECONDS}s")
    print("Press Ctrl+C to stop.\n")

    while True:
        maybe_trigger_crash_sequence()
        send(generate_sensor_reading())
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n[simulate_esp32.py] Stopped.")
