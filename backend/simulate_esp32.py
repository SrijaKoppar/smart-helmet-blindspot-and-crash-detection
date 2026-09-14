"""
simulate_esp32.py
Mimics the ESP32 helmet sending periodic sensor readings to the Flask
backend, so the dashboard can be built and tested before hardware is
ready (Phase 2/3/4). Run this in a separate terminal, alongside app.py.

Usage:
    python simulate_esp32.py
    (Ctrl+C to stop)
"""

import requests
import random
import time

SERVER_URL = "http://localhost:5000/api/ingest"
INTERVAL_SECONDS = 1.5


def classify_severity(distance):
    """Mimics the same severity thresholds the ESP32 firmware would use."""
    if distance is None:
        return "none"
    if distance < 50:
        return "high"
    elif distance < 150:
        return "caution"
    return "none"


def decide_active_alert(left_sev, right_sev, crash_flag, head_turn_active):
    """Mimics simplified priority arbitration: crash > blind-spot, and
    head-turn suppresses an alert on that side."""
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


def generate_fake_reading():
    """Generates one plausible sensor reading, with occasional random events."""
    left_distance = round(random.uniform(20, 400), 1)
    right_distance = round(random.uniform(20, 400), 1)

    # Rare random events to keep the feed interesting during dev/testing
    crash_flag = 1 if random.random() < 0.02 else 0
    head_turn_active = 1 if random.random() < 0.08 else 0

    left_severity = classify_severity(left_distance)
    right_severity = classify_severity(right_distance)
    active_alert = decide_active_alert(
        left_severity, right_severity, crash_flag, head_turn_active
    )

    return {
        "left_distance": left_distance,
        "right_distance": right_distance,
        "left_severity": left_severity,
        "right_severity": right_severity,
        "head_turn_active": head_turn_active,
        "crash_flag": crash_flag,
        "active_alert": active_alert,
        "event_type": "sensor_update",
        "notes": "Simulated reading"
    }


def run():
    print(f"[simulate_esp32.py] Sending fake readings to {SERVER_URL} every {INTERVAL_SECONDS}s")
    print("Press Ctrl+C to stop.\n")

    while True:
        payload = generate_fake_reading()
        try:
            response = requests.post(SERVER_URL, json=payload, timeout=3)
            if response.status_code == 201:
                print(f"Sent: L={payload['left_distance']}cm R={payload['right_distance']}cm "
                      f"alert={payload['active_alert']}")
            else:
                print(f"Server returned {response.status_code}: {response.text}")
        except requests.exceptions.ConnectionError:
            print("Could not reach Flask server - is app.py running?")

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n[simulate_esp32.py] Stopped.")
