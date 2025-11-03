from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timedelta
from app.core.securitycore import get_password_hash, create_access_token, verify_password, get_current_user
from app.basemodels.usermodel import UserRegister, UserLogin, ForgotPasswordRequest, ResetPasswordRequest, UserUpdate
from app.core.smtp_otp import send_otp, verify_otp
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()


# MongoDB connection
client = MongoClient(os.getenv("MONGO_URL"))
db = client[os.getenv("DB_NAME")]
users_collection = db["users"]


@router.post("/registration", status_code=status.HTTP_201_CREATED)
async def register_user(user: UserRegister):
    existing_user = users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user.password)

    user_doc = {
        "email": user.email,
        "password": hashed_password,
        "male": user.male,
        "age": user.age,
        "currentSmoker": user.currentSmoker,
        "cigsPerDay": user.cigsPerDay,
        "BPMeds": user.BPMeds,
        "prevalentStroke": user.prevalentStroke,
        "prevalentHyp": user.prevalentHyp,
        "diabetes": user.diabetes,
        "totChol": user.totChol,
        "sysBP": user.sysBP,
        "diaBP": user.diaBP,
        "BMI": user.BMI,
        "glucose": user.glucose,
        "created_at": datetime.utcnow(),
    }

    users_collection.insert_one(user_doc)

    access_token_expires = timedelta(minutes=60 * 24)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    return {
        "status": "success",
        "message": "User registered successfully",
        "access_token": access_token,
        "token_type": "bearer"
    }

# login route
@router.post("/login", status_code=status.HTTP_200_OK)
async def login_user(user: UserLogin):
    existing_user = users_collection.find_one({"email": user.email})
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(user.password, existing_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid password")
    access_token_expires = timedelta(minutes=60 * 24) 
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    user_info = {k: v for k, v in existing_user.items() if k != "password"}
    user_info["_id"] = str(user_info["_id"]) 

    return {
        "status": "success",
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_info
    }


# forgot password routes
@router.post("/forgot-password/send", status_code=status.HTTP_200_OK)
async def send_forgot_password_otp(request: ForgotPasswordRequest):
    user = users_collection.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        send_otp(request.email)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send OTP: {str(e)}")

    return {"status": "success", "message": f"OTP sent to {request.email}"}

@router.post("/forgot-password/verify", status_code=status.HTTP_200_OK)
async def verify_and_reset_password(request: ResetPasswordRequest):
    user = users_collection.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    otp_verified = verify_otp(request.email, request.otp)
    if not otp_verified:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    hashed_password = get_password_hash(request.new_password)
    users_collection.update_one(
        {"email": request.email},
        {"$set": {"password": hashed_password}}
    )

    return {
        "status": "success",
        "message": "Password reset successfully. You can now log in with your new password."
    }

# update user
@router.put("/update-user", status_code=status.HTTP_200_OK)
async def update_user(data: UserUpdate, current_user: dict = Depends(get_current_user)):
    user_email = current_user["email"]

    update_fields = {k: v for k, v in data.dict().items() if v is not None}

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    if "password" in update_fields:
        update_fields["password"] = get_password_hash(update_fields["password"])

    result = users_collection.update_one(
        {"email": user_email},
        {"$set": update_fields}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="No changes made")

    updated_user = users_collection.find_one({"email": user_email})
    updated_user["_id"] = str(updated_user["_id"])
    updated_user.pop("password", None)  

    return {
        "status": "success",
        "message": "User profile updated successfully",
        "updated_user": updated_user
    }

# get current user function
@router.get("/me", status_code=status.HTTP_200_OK)
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Returns the authenticated user's profile information.
    Requires a valid JWT Bearer token.
    """
    return {
        "status": "success",
        "user": current_user
    }

# delete user route
@router.delete("/delete-user", status_code=status.HTTP_200_OK)
async def delete_user(current_user: dict = Depends(get_current_user)):
    user_email = current_user["email"]

    result = users_collection.delete_one({"email": user_email})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found or already deleted")

    return {
        "status": "success",
        "message": f"Account for '{user_email}' deleted successfully"
    }