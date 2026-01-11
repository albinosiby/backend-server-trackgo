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

INTERVAL_SECONDS = 120


def fetch_gps_data():
    while True:
        try:
            response = requests.post(API_URL, json=API_BODY, timeout=30)

            if response.status_code == 200:
                data = response.json()

                live_data = data.get("response", {}).get("response", {}).get("LiveData", [])

                for bus in live_data:
                    if bus.get("Reg_No") == "KL-59-L-3717":
                        db.reference(
                            "/organizations/obnpZfRSukYavktpNiea5Q6p4WB2/bus_location/KL-59-L-3717"
                        ).update({
                            "latitude": bus.get("Lat"),
                            "longitude": bus.get("Lon"),
                            "speed": bus.get("Speed"),
                            "timestamp": int(time.time() * 1000)
                        })

                # keep api logs
                db.reference("/api_logs").push({
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": response.status_code,
                    "response": data
                })

                print("Bus location updated")

            else:
                print("API error:", response.status_code)

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
