from fastapi import APIRouter, HTTPException, Depends, status
from app.core.securitycore import get_current_user
from app.core.mlllm import predict_cardiovascular_risk, generate_medical_report, analyze_ecg_with_llm
from pymongo import MongoClient
from firebase_admin import credentials, db
import firebase_admin
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

client = MongoClient(os.getenv("MONGO_URL"))
db_mongo = client[os.getenv("DB_NAME")]
users_collection = db_mongo["users"]

FIREBASE_CRED_PATH = os.getenv("FIREBASE_CRED_PATH")
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL")

if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CRED_PATH)
    firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DB_URL})


@router.get("/predict", status_code=status.HTTP_200_OK)
async def predict_cardio_risk(current_user: dict = Depends(get_current_user)):
    try:
        user_email = current_user["email"]
        user_doc = users_collection.find_one({"email": user_email})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = {k: user_doc.get(k, 0) for k in [
            "male","age","currentSmoker","cigsPerDay","BPMeds",
            "prevalentStroke","prevalentHyp","diabetes","totChol",
            "sysBP","diaBP","BMI","glucose"
        ]}

        user_id = str(user_doc["_id"])
        ref = db.reference(f"/users/{user_id}/realtime")
        realtime_data = ref.get()

        # Default safe values
        heart_rate = None
        prediction = None
        llm_report = {
            "diagnosis_summary": "Awaiting live heart rate data to generate prediction.",
            "lifestyle_suggestions": {
                "diet": "Maintain a balanced diet rich in vegetables, fruits, and lean proteins.",
                "exercise": "Engage in regular moderate exercise (e.g., brisk walking, cycling).",
                "habits": "Avoid smoking and reduce alcohol intake.",
                "medical_followup": "Regularly monitor blood pressure and glucose levels."
            }
        }

        # Only generate prediction if HR is available
        if realtime_data and "heart_rate" in realtime_data:
            heart_rate = realtime_data["heart_rate"]
            prediction = predict_cardiovascular_risk(user_data, heart_rate)
            llm_report = generate_medical_report(user_data, prediction)

        return {
            "status": "success",
            "user_id": user_id,
            "heart_rate": heart_rate,
            "prediction": prediction,
            "ai_report": llm_report
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    
@router.get("/ecg", status_code=status.HTTP_200_OK)
async def analyze_ecg_data(current_user: dict = Depends(get_current_user)):
    try:
        user_email = current_user["email"]
        user_doc = users_collection.find_one({"email": user_email})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")

        user_id = str(user_doc["_id"])
        ref = db.reference(f"/users/{user_id}/realtime")
        realtime_data = ref.get()

        if not realtime_data or "ecg_data" not in realtime_data:
            return {
                "status": "pending",
                "user_id": user_id,
                "message": "Awaiting ECG data from device.",
                "ecg_data": [],
                "ai_ecg_insight": None
            }

        ecg_data = realtime_data["ecg_data"]
        heart_rate = realtime_data.get("heart_rate", None)

        user_data = {
            "age": user_doc.get("age", 0),
            "sex": "Male" if user_doc.get("male", 0) == 1 else "Female",
            "has_hypertension": user_doc.get("prevalentHyp", 0),
            "has_diabetes": user_doc.get("diabetes", 0)
        }

        ai_ecg_insight = analyze_ecg_with_llm(user_data, heart_rate, ecg_data)

        return {
            "status": "success",
            "user_id": user_id,
            "message": "ECG data analyzed successfully.",
            "heart_rate": heart_rate,
            "ecg_data_length": len(ecg_data),
            "ai_ecg_insight": ai_ecg_insight
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")