from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.routes.user import router as user_router
from app.routes.predict import router as predict_router
import time
import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       
    allow_credentials=True,
    allow_methods=["*"],      
    allow_headers=["*"],
)


app = FastAPI()
app.include_router(user_router)
app.include_router(predict_router)