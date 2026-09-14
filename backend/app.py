"""
app.py
Entry point for the Smart Helmet dashboard backend (Flask).
"""

from flask import Flask, jsonify
from models import init_db, get_connection
from routes import api          # <-- ADD THIS LINE

app = Flask(__name__)
app.register_blueprint(api)     # <-- ADD THIS LINE


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
    app.run(host="0.0.0.0", port=5000, debug=True)