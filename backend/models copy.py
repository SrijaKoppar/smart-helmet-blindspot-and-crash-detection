"""
models.py
Handles SQLite database setup and connection for the Smart Helmet dashboard.

Table: readings
Stores every sensor reading / event coming from the helmet (or the
simulator script, during development before hardware is ready).
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "helmet_data.db")


def get_connection():
    """Returns a new SQLite connection. Each request should open and
    close its own connection - simplest safe pattern for a small Flask app."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


def init_db():
    """Creates the readings table if it doesn't already exist.
    Safe to call every time the app starts."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            left_distance REAL,
            right_distance REAL,
            left_severity TEXT DEFAULT 'none',
            right_severity TEXT DEFAULT 'none',
            head_turn_active INTEGER DEFAULT 0,
            crash_flag INTEGER DEFAULT 0,
            active_alert TEXT DEFAULT 'none',
            event_type TEXT DEFAULT 'sensor_update',
            notes TEXT DEFAULT ''
        )
    """)

    conn.commit()
    conn.close()
    print(f"[models.py] Database ready at {DB_PATH}")


if __name__ == "__main__":
    # Allows running `python models.py` directly to (re)initialize the DB
    init_db()
