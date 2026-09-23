"""
routes.py
All API endpoints for the Smart Helmet dashboard backend.

Design note: the ESP32 (or the simulator, for now) is responsible for
running the actual arbitration logic (severity classification, TTC
calculation, crash confirmation staging, head-turn masking). This
backend just stores and serves that data - it does NOT re-derive any
of it itself. This keeps the dashboard a pure visualization layer,
consistent with the project's core claim living in the firmware's
arbitration engine, not the web app.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from models import get_connection

api = Blueprint("api", __name__)


# ---------- Helpers ----------

def row_to_dict(row):
    """Converts a sqlite3.Row into a plain dict so it can be JSON-serialized."""
    return {key: row[key] for key in row.keys()}


def insert_reading(data):
    """Shared insert logic used by both /api/ingest and /api/simulate."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO readings (
            timestamp, left_distance, right_distance,
            left_severity, right_severity, left_ttc, right_ttc,
            head_turn_active, crash_flag, crash_stage,
            active_alert, event_type, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        data.get("left_distance"),
        data.get("right_distance"),
        data.get("left_severity", "none"),
        data.get("right_severity", "none"),
        data.get("left_ttc"),
        data.get("right_ttc"),
        int(data.get("head_turn_active", 0)),
        int(data.get("crash_flag", 0)),
        data.get("crash_stage", "none"),
        data.get("active_alert", "none"),
        data.get("event_type", "sensor_update"),
        data.get("notes", "")
    ))

    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


# ---------- POST /api/ingest ----------

@api.route("/api/ingest", methods=["POST"])
def ingest():
    """
    Receives one sensor reading / event from the helmet (or simulator).
    Expected JSON body (all fields optional except we fill sane defaults):
    {
        "left_distance": 120.5,          # cm
        "right_distance": 300.0,         # cm
        "left_severity": "caution",      # none | caution | high
        "right_severity": "none",
        "left_ttc": 2.4,                 # seconds to collision, null if not closing
        "right_ttc": null,
        "head_turn_active": 0,           # 0 or 1
        "crash_flag": 0,                 # 0 or 1 - final confirmed state only
        "crash_stage": "none",           # none | impact_detected | confirmed | false_alarm
        "active_alert": "blindspot_left",  # none | blindspot_left | blindspot_right | crash
        "event_type": "sensor_update",   # sensor_update | crash | head_turn | manual_sim
        "notes": ""
    }
    """
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    new_id = insert_reading(data)
    return jsonify({"status": "inserted", "id": new_id}), 201


# ---------- GET /api/latest ----------

@api.route("/api/latest", methods=["GET"])
def latest():
    """Returns the single most recent reading. Used by the live dashboard."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM readings ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()

    if row is None:
        return jsonify({"message": "No readings yet"}), 404

    return jsonify(row_to_dict(row))


# ---------- GET /api/history?limit=50 ----------

@api.route("/api/history", methods=["GET"])
def history():
    """Returns the last N readings, most recent first. Default limit: 50."""
    limit = request.args.get("limit", default=50, type=int)
    limit = max(1, min(limit, 500))  # clamp to a sane range

    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM readings ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()

    return jsonify([row_to_dict(r) for r in rows])


# ---------- GET /api/stats ----------

@api.route("/api/stats", methods=["GET"])
def stats():
    """
    Returns summary counts used on the Event Log page:
    - total readings logged
    - total confirmed crashes
    - total alerts (any non-'none' active_alert)
    - total suppressed alerts (head_turn_active = 1, i.e. intent-masking fired)
    - total crash false alarms caught by the two-stage confirmation check
    """
    conn = get_connection()

    total_readings = conn.execute(
        "SELECT COUNT(*) AS c FROM readings"
    ).fetchone()["c"]

    total_crashes = conn.execute(
        "SELECT COUNT(*) AS c FROM readings WHERE crash_flag = 1"
    ).fetchone()["c"]

    total_alerts = conn.execute(
        "SELECT COUNT(*) AS c FROM readings WHERE active_alert != 'none'"
    ).fetchone()["c"]

    total_suppressed = conn.execute(
        "SELECT COUNT(*) AS c FROM readings WHERE head_turn_active = 1"
    ).fetchone()["c"]

    total_false_alarms = conn.execute(
        "SELECT COUNT(*) AS c FROM readings WHERE crash_stage = 'false_alarm'"
    ).fetchone()["c"]

    conn.close()

    return jsonify({
        "total_readings": total_readings,
        "total_crashes": total_crashes,
        "total_alerts": total_alerts,
        "total_suppressed": total_suppressed,
        "total_false_alarms": total_false_alarms
    })


# ---------- POST /api/simulate ----------

@api.route("/api/simulate", methods=["POST"])
def simulate():
    """
    Manually triggers a demo scenario - used by the dashboard's demo buttons.

    Expected JSON body:
    { "event_type": "left_threat" | "right_threat" | "crash_confirmed" |
                     "crash_false_alarm" | "head_turn" }

    Note: "crash_confirmed" and "crash_false_alarm" each insert TWO rows in
    sequence (impact_detected, then confirmed/false_alarm) to demonstrate
    the two-stage crash confirmation logic - not just a single event.
    """
    data = request.get_json(silent=True) or {}
    event_type = data.get("event_type")

    single_step_presets = {
        "left_threat": {
            "left_distance": 45.0, "right_distance": 300.0,
            "left_severity": "high", "right_severity": "none",
            "left_ttc": 0.9, "right_ttc": None,
            "head_turn_active": 0, "crash_flag": 0, "crash_stage": "none",
            "active_alert": "blindspot_left", "event_type": "manual_sim",
            "notes": "Simulated: vehicle closing fast on left (TTC 0.9s)"
        },
        "right_threat": {
            "left_distance": 300.0, "right_distance": 50.0,
            "left_severity": "none", "right_severity": "high",
            "left_ttc": None, "right_ttc": 1.1,
            "head_turn_active": 0, "crash_flag": 0, "crash_stage": "none",
            "active_alert": "blindspot_right", "event_type": "manual_sim",
            "notes": "Simulated: vehicle closing fast on right (TTC 1.1s)"
        },
        "head_turn": {
            "left_distance": 40.0, "right_distance": 300.0,
            "left_severity": "high", "right_severity": "none",
            "left_ttc": 0.8, "right_ttc": None,
            "head_turn_active": 1, "crash_flag": 0, "crash_stage": "none",
            "active_alert": "none", "event_type": "manual_sim",
            "notes": "Simulated: rider head-turn suppressed left alert"
        },
    }

    # Two-stage sequences: each inserts an impact_detected row, then a
    # resolution row, mirroring the real firmware's confirmation window.
    two_stage_presets = {
        "crash_confirmed": [
            {
                "left_distance": None, "right_distance": None,
                "left_severity": "none", "right_severity": "none",
                "left_ttc": None, "right_ttc": None,
                "head_turn_active": 0, "crash_flag": 0, "crash_stage": "impact_detected",
                "active_alert": "crash", "event_type": "manual_sim",
                "notes": "Simulated: impact spike detected, confirming..."
            },
            {
                "left_distance": None, "right_distance": None,
                "left_severity": "none", "right_severity": "none",
                "left_ttc": None, "right_ttc": None,
                "head_turn_active": 0, "crash_flag": 1, "crash_stage": "confirmed",
                "active_alert": "crash", "event_type": "crash",
                "notes": "Simulated: no motion after impact - crash confirmed"
            },
        ],
        "crash_false_alarm": [
            {
                "left_distance": None, "right_distance": None,
                "left_severity": "none", "right_severity": "none",
                "left_ttc": None, "right_ttc": None,
                "head_turn_active": 0, "crash_flag": 0, "crash_stage": "impact_detected",
                "active_alert": "crash", "event_type": "manual_sim",
                "notes": "Simulated: impact spike detected, confirming..."
            },
            {
                "left_distance": None, "right_distance": None,
                "left_severity": "none", "right_severity": "none",
                "left_ttc": None, "right_ttc": None,
                "head_turn_active": 0, "crash_flag": 0, "crash_stage": "false_alarm",
                "active_alert": "none", "event_type": "manual_sim",
                "notes": "Simulated: motion resumed (pothole) - false alarm rejected"
            },
        ],
    }

    if event_type in single_step_presets:
        new_id = insert_reading(single_step_presets[event_type])
        return jsonify({"status": "simulated", "event_type": event_type, "id": new_id}), 201

    if event_type in two_stage_presets:
        last_id = None
        for step in two_stage_presets[event_type]:
            last_id = insert_reading(step)
        return jsonify({"status": "simulated", "event_type": event_type, "id": last_id}), 201

    valid_types = list(single_step_presets.keys()) + list(two_stage_presets.keys())
    return jsonify({
        "error": f"Unknown event_type '{event_type}'. Must be one of: {valid_types}"
    }), 400
