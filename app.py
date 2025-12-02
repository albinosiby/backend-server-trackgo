from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import json, os

# Flask app
app = Flask(__name__)

# Firebase setup
cred_json = os.environ.get("FIREBASE_SERVICE_KEY")
if not cred_json:
    raise Exception("Firebase service key missing!")

cred_dict = json.loads(cred_json)
cred = credentials.Certificate(cred_dict)

firebase_admin.initialize_app(cred, {
    "databaseURL": os.environ["FIREBASE_DB_URL"]
})

@app.route("/", methods=["GET", "POST"])
def receive_data():
    timestamp = datetime.utcnow().isoformat()

    raw_body = request.get_data(as_text=True)
    query_params = request.args.to_dict()
    headers = dict(request.headers)

    data_to_store = {
        "timestamp": timestamp,
        "raw_body": raw_body,
        "query_params": query_params,
        "headers": headers
    }

    db.reference("/raw_logs").push(data_to_store)

    print("\n--- RECEIVED DATA ---")
    print(json.dumps(data_to_store, indent=2))

    return "OK"

@app.route("/test")
def test():
    return "Server running"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
