from flask import Flask
import requests
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import json
import os
import threading
import time

app = Flask(__name__)

# ---------- FIREBASE SETUP ----------
cred_json = os.environ.get("FIREBASE_SERVICE_KEY")
if not cred_json:
    raise Exception("FIREBASE_SERVICE_KEY not set")

cred_dict = json.loads(cred_json)
cred = credentials.Certificate(cred_dict)

firebase_admin.initialize_app(cred, {
    "databaseURL": "https://bus-management-c8612-default-rtdb.firebaseio.com"
})

# ---------- LIVETRACE API DETAILS ----------
API_URL = "http://livetrace.live:1234/Live_All"

API_BODY = {
    "header": {
        "Version": "1.0",
        "clientName": "API_LiveTrace"
    },
    "request": {
        "userid": "vjectest",
        "key": "testkey"
    }
}

# ---------- RATE-LIMIT PROTECTION ----------
lock = threading.Lock()
last_call_time = 0
INTERVAL_SECONDS = 120  # 2 minutes

def fetch_gps_data():
    global last_call_time

    while True:
        with lock:
            now = time.time()
            if now - last_call_time < INTERVAL_SECONDS:
                time.sleep(5)
                continue

            last_call_time = now

        try:
            response = requests.post(API_URL, json=API_BODY, timeout=30)

            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception:
                    data = {"raw": response.text}

                db.reference("/api_logs").push({
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": response.status_code,
                    "response": data
                })

                print("GPS data stored")

            else:
                print("API error:", response.status_code, response.text)

        except Exception as e:
            print("LiveTrace API call failed:", e)

        time.sleep(INTERVAL_SECONDS)


# ---------- START BACKGROUND THREAD (ONCE) ----------
def start_background_task():
    t = threading.Thread(target=fetch_gps_data, daemon=True)
    t.start()

start_background_task()

@app.route("/")
def home():
    return "LiveTrace API polling service running"

@app.route("/test")
def test():
    return "Server OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
