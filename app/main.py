from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.routes.user import router as user_router
from app.routes.predict import router as predict_router
import os, time

load_dotenv()

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(user_router)
app.include_router(predict_router)

@app.api_route("/health", methods=["GET", "HEAD"])
def health_check(request: Request):
    if request.method == "HEAD":
        return {}  # No body needed for HEAD
    return {"status": "ok", "timestamp": time.time()}
