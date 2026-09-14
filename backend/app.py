"""
app.py
Entry point for the Smart Helmet dashboard backend (Flask).

Phase 1 scope:
- Initialize the database on startup
- Provide a /health endpoint to confirm the server + DB are working

API endpoints (ingest, latest, history, stats, simulate) are added
in Phase 2 - kept out of this file for now to keep Phase 1 minimal
and easy to verify.
"""

from flask import Flask, jsonify
from models import init_db, get_connection

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health_check():
    """Confirms the Flask server is running AND can talk to the database."""
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"

    return jsonify({
        "status": "OK",
        "database": db_status
    })


if __name__ == "__main__":
    init_db()
    # host="0.0.0.0" so the ESP32 (on the same WiFi network) can reach
    # this server later in Phase 5, not just localhost
    app.run(host="0.0.0.0", port=5000, debug=True)
