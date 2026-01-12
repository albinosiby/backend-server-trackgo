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

# ---------- LIVETRACE API ----------
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

INTERVAL_SECONDS = 121


def fetch_gps_data():
    ORG_ID = "obnpZfRSukYavktpNiea5Q6p4WB2"

    while True:
        try:
            # 1️⃣ Read bus IDs from Firebase
            bus_locations = db.reference(
                f"/organizations/{ORG_ID}/bus_location"
            ).get() or {}

            bus_ids = set(bus_locations.keys())
            print("Firebase bus IDs:", bus_ids)

            # 2️⃣ Call LiveTrace API
            response = requests.post(API_URL, json=API_BODY, timeout=30)

            if response.status_code != 200:
                print("API error:", response.status_code)
                time.sleep(INTERVAL_SECONDS)
                continue

            data = response.json()
            live_data = data.get("response", {}).get("response", {}).get("LiveData", [])

            # 3️⃣ Update bus locations
            for bus in live_data:
                reg_no = bus.get("Reg_No")

                if reg_no in bus_ids:
                    try:
                        # Parse time string "2026-01-12 10:02:31"
                        time_str = bus.get("Time")
                        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                        ts = int(dt.timestamp() * 1000)
                    except Exception:
                        ts = int(time.time() * 1000)

                    db.reference(
                        f"/organizations/{ORG_ID}/bus_location/{reg_no}"
                    ).update({
                        "latitude": bus.get("Lat"),
                        "longitude": bus.get("Lon"),
                        "speed": bus.get("Speed"),
                        "timestamp": ts
                    })

                    print(f"✅ Updated location for {reg_no}")

            # 4️⃣ Rewrite single API log
            db.reference("/api_logs/latest").set({
                "timestamp": datetime.utcnow().isoformat(),
                "status": response.status_code,
                "response": data
            })

        except Exception as e:
            print("Error:", e)

        time.sleep(INTERVAL_SECONDS)

# ---------- START BACKGROUND THREAD ----------
threading.Thread(target=fetch_gps_data, daemon=True).start()


# ---------- FLASK ROUTES ----------
@app.route("/")
def home():
    return "LiveTrace API polling service running"


@app.route("/test")
def test():
    return "Server OK"
