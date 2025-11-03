import os
import time
import random
from datetime import datetime
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db

load_dotenv()

FIREBASE_CRED_PATH = os.getenv("FIREBASE_CRED_PATH")
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL")       
USER_ID = os.getenv("FIREBASE_USER_ID", "user123")

if not FIREBASE_CRED_PATH or not FIREBASE_DB_URL:
    raise EnvironmentError("Missing Firebase config in .env (FIREBASE_CRED_PATH or FIREBASE_DB_URL)")

cred = credentials.Certificate(FIREBASE_CRED_PATH)
firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DB_URL})

user_path = f"/users/{USER_ID}/realtime"

def generate_dummy_data():
    heart_rate = random.randint(60, 100)
    ecg_signal = [round(random.uniform(-0.5, 0.5), 3) for _ in range(50)] 
    return {
        "heart_rate": heart_rate,
        "ecg_data": ecg_signal,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def update_firebase():
    ref = db.reference(user_path)
    print(f" Sending dummy HR + ECG data to {user_path} every 60 seconds...\n")
    while True:
        data = generate_dummy_data()
        ref.set(data)
        print(f" [{datetime.now().strftime('%H:%M:%S')}] Updated Firebase with: HR={data['heart_rate']}")
        time.sleep(60)

if __name__ == "__main__":
    try:
        update_firebase()
    except KeyboardInterrupt:
        print("\n Simulation stopped manually.")
