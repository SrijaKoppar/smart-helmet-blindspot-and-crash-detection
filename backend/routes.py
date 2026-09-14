"""
routes.py
All API endpoints for the Smart Helmet dashboard backend.

Design note: the ESP32 (or the simulator, for now) is responsible for
running the actual arbitration logic (severity classification, priority
decision, head-turn masking). This backend just stores and serves that
data - it does NOT re-derive severity/arbitration itself. This keeps the
dashboard a pure visualization layer, consistent with the project's
core claim living in the firmware's arbitration engine, not the web app.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from models import get_connection

api = Blueprint("api", __name__)


# ---------- Helpers ----------

def row_to_dict(row):
    """Converts a sqlite3.Row into a plain dict so it can be JSON-serialized."""
    return {key: row[key] for key in row.keys()}


# ---------- POST /api/ingest ----------

@api.route("/api/ingest", methods=["POST"])
def ingest():
    """
    Receives one sensor reading / event from the helmet (or simulator).
    Expected JSON body (all fields optional except we fill sane defaults):
    {
        "left_distance": 120.5,
        "right_distance": 300.0,
        "left_severity": "caution",     # none | caution | high
        "right_severity": "none",
        "head_turn_active": 0,          # 0 or 1
        "crash_flag": 0,                # 0 or 1
        "active_alert": "blindspot_left",  # none | blindspot_left | blindspot_right | crash
        "event_type": "sensor_update",  # sensor_update | crash | head_turn | manual_sim
        "notes": ""
    }
    """
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO readings (
            timestamp, left_distance, right_distance,
            left_severity, right_severity, head_turn_active,
            crash_flag, active_alert, event_type, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        data.get("left_distance"),
        data.get("right_distance"),
        data.get("left_severity", "none"),
        data.get("right_severity", "none"),
        int(data.get("head_turn_active", 0)),
        int(data.get("crash_flag", 0)),
        data.get("active_alert", "none"),
        data.get("event_type", "sensor_update"),
        data.get("notes", "")
    ))

    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

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
    - total crash events
    - total alerts (any non-'none' active_alert)
    - total suppressed alerts (head_turn_active = 1, i.e. intent-masking fired)
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

    conn.close()

    return jsonify({
        "total_readings": total_readings,
        "total_crashes": total_crashes,
        "total_alerts": total_alerts,
        "total_suppressed": total_suppressed
    })


# ---------- POST /api/simulate ----------

@api.route("/api/simulate", methods=["POST"])
def simulate():
    """
    Manually triggers a demo scenario - used by the dashboard's
    'Simulate Left Threat / Crash / Head-Turn' buttons in Phase 4.

    Expected JSON body: { "event_type": "left_threat" | "right_threat" | "crash" | "head_turn" }
    """
    data = request.get_json(silent=True) or {}
    event_type = data.get("event_type")

    presets = {
        "left_threat": {
            "left_distance": 35.0, "right_distance": 300.0,
            "left_severity": "high", "right_severity": "none",
            "head_turn_active": 0, "crash_flag": 0,
            "active_alert": "blindspot_left", "event_type": "manual_sim",
            "notes": "Simulated: vehicle closing fast on left"
        },
        "right_threat": {
            "left_distance": 300.0, "right_distance": 40.0,
            "left_severity": "none", "right_severity": "high",
            "head_turn_active": 0, "crash_flag": 0,
            "active_alert": "blindspot_right", "event_type": "manual_sim",
            "notes": "Simulated: vehicle closing fast on right"
        },
        "crash": {
            "left_distance": None, "right_distance": None,
            "left_severity": "none", "right_severity": "none",
            "head_turn_active": 0, "crash_flag": 1,
            "active_alert": "crash", "event_type": "manual_sim",
            "notes": "Simulated: crash impact confirmed"
        },
        "head_turn": {
            "left_distance": 40.0, "right_distance": 300.0,
            "left_severity": "high", "right_severity": "none",
            "head_turn_active": 1, "crash_flag": 0,
            "active_alert": "none", "event_type": "manual_sim",
            "notes": "Simulated: rider head-turn suppressed left alert"
        },
    }

    if event_type not in presets:
        return jsonify({
            "error": f"Unknown event_type '{event_type}'. Must be one of: {list(presets.keys())}"
        }), 400

    payload = presets[event_type]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO readings (
            timestamp, left_distance, right_distance,
            left_severity, right_severity, head_turn_active,
            crash_flag, active_alert, event_type, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        payload["left_distance"], payload["right_distance"],
        payload["left_severity"], payload["right_severity"],
        payload["head_turn_active"], payload["crash_flag"],
        payload["active_alert"], payload["event_type"], payload["notes"]
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    return jsonify({"status": "simulated", "event_type": event_type, "id": new_id}), 201
