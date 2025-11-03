import os
import joblib
import pandas as pd
import numpy as np
from openai import OpenAI
import warnings
import requests


warnings.filterwarnings("ignore", message="Trying to unpickle estimator LogisticRegression")

MODEL_PATH = os.getenv("MODEL_PATH")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def load_model():
    if MODEL_PATH.startswith("http"):
        print(f"[INFO] Downloading model from {MODEL_PATH} ...")
        response = requests.get(MODEL_PATH)
        if response.status_code == 200:
            from io import BytesIO
            model_bytes = BytesIO(response.content)
            model = joblib.load(model_bytes)
            print("[INFO] Model loaded successfully from URL.")
            return model
        else:
            raise FileNotFoundError(f"Failed to download model. HTTP {response.status_code}")
    else:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError("Model file not found")
        print(f"[INFO] Loading model from local path: {MODEL_PATH}")
        return joblib.load(MODEL_PATH)

model = load_model()

def predict_cardiovascular_risk(user_data: dict, heart_rate: float):
    features = [
        "male", "age", "currentSmoker", "cigsPerDay", "BPMeds",
        "prevalentStroke", "prevalentHyp", "diabetes", "totChol",
        "sysBP", "diaBP", "BMI", "glucose", "heart_rate"
    ]
    input_data = {**user_data, "heart_rate": heart_rate}
    for f in features:
        if f not in input_data: input_data[f] = 0
    df = pd.DataFrame([input_data], columns=features)
    risk_prob = model.predict_proba(df.values)[0][1]

    return {
        "risk_probability": float(np.round(risk_prob, 3)),
        "risk_percentage": float(np.round(risk_prob * 100, 2))
    }

def generate_medical_report(user_data: dict, prediction: dict):
    prompt = f"""
    You are a medical AI assistant. Given the following patient details and model prediction,
    provide a short diagnostic summary and structured lifestyle advice.

    Patient Details: {user_data}
    Model Prediction: {prediction}

    Output format (JSON only):
    {{
        "diagnosis_summary": " Use Patient Details, Model Prediction to give the current diagnosis with accuracy ",
        "lifestyle_suggestions": {{ use Use Patient Details, Model Prediction to make suggestions
            "diet": "<specific dietary suggestions>",
            "exercise": "<recommended physical activity>",
            "habits": "<changes to smoking/alcohol/sleep>",
            "medical_followup": "<tests, visits, or medications to consider>"
        }}
    }}
    """

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        temperature=0.3
    )
    try:
        text = response.output[0].content[0].text
    except Exception:
        text = "LLM response parsing failed."
    return text

def analyze_ecg_with_llm(user_data: dict, heart_rate: float, ecg_data: list):
    prompt = f"""
    You are a medical AI cardiology assistant. Analyze the following ECG signal data
    and provide a structured medical insight.

    Patient Info: {user_data}
    Heart Rate: {heart_rate}
    ECG Data (sampled): {ecg_data[:500]}

    Analyze for rhythm, abnormalities (like AFib, bradycardia, tachycardia, ischemia),
    and include medical interpretation and suggested actions.

    Output format (JSON only):
    {{
        "heart_rate_analysis": "<normal/brady/tachy with brief reasoning>",
        "rhythm_assessment": "<sinus rhythm / AFib / arrhythmia etc.>",
        "abnormalities_detected": "<summary of possible ECG abnormalities>",
        "medical_interpretation": "<professional summary for doctor>",
        "recommendations": "<suggested next steps or follow-up actions>"
    }}
    """

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        temperature=0.3
    )

    try:
        return response.output[0].content[0].text
    except Exception:
        return "ECG analysis failed to parse from LLM output."