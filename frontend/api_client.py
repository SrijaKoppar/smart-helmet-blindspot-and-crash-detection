"""
api_client.py
Small wrapper around the Flask backend's REST API, used by the Streamlit
dashboard. Keeping this separate from dashboard.py so the UI code doesn't
get cluttered with requests/error-handling boilerplate.
"""

import requests

BASE_URL = "http://localhost:5000"
TIMEOUT_SECONDS = 3


def get_latest():
    """
    Returns the most recent reading as a dict, or None if:
    - the backend has no readings yet (404), or
    - the backend is unreachable
    """
    try:
        response = requests.get(f"{BASE_URL}/api/latest", timeout=TIMEOUT_SECONDS)
        if response.status_code == 200:
            return response.json()
        return None  # covers the 404 "No readings yet" case
    except requests.exceptions.RequestException:
        return None


def get_history(limit=30):
    """Returns the last `limit` readings as a list of dicts (most recent first)."""
    try:
        response = requests.get(
            f"{BASE_URL}/api/history", params={"limit": limit}, timeout=TIMEOUT_SECONDS
        )
        if response.status_code == 200:
            return response.json()
        return []
    except requests.exceptions.RequestException:
        return []


def get_stats():
    """Returns summary stats as a dict, or a zeroed-out dict if unreachable."""
    try:
        response = requests.get(f"{BASE_URL}/api/stats", timeout=TIMEOUT_SECONDS)
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException:
        pass
    return {"total_readings": 0, "total_crashes": 0, "total_alerts": 0, "total_suppressed": 0}


def post_simulate(event_type):
    """Triggers a demo scenario on the backend. Returns True on success."""
    try:
        response = requests.post(
            f"{BASE_URL}/api/simulate", json={"event_type": event_type}, timeout=TIMEOUT_SECONDS
        )
        return response.status_code == 201
    except requests.exceptions.RequestException:
        return False


def is_backend_reachable():
    """Quick check used to show a friendly warning if Flask isn't running."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT_SECONDS)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False
