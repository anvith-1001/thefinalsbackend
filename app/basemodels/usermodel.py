from pydantic import BaseModel, EmailStr, Field

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=72)
    male: int
    age: int
    currentSmoker: int
    cigsPerDay: float
    BPMeds: int
    prevalentStroke: int
    prevalentHyp: int
    diabetes: int
    totChol: float
    sysBP: float
    diaBP: float
    BMI: float
    glucose: float

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    male: int | None = None
    age: int | None = None
    currentSmoker: int | None = None
    cigsPerDay: float | None = None
    BPMeds: int | None = None
    prevalentStroke: int | None = None
    prevalentHyp: int | None = None
    diabetes: int | None = None
    totChol: float | None = None
    sysBP: float | None = None
    diaBP: float | None = None
    BMI: float | None = None
    glucose: float | None = None
    password: str | None = Field(None, min_length=6, max_length=72)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=4, max_length=6)
    new_password: str = Field(..., min_length=6, max_length=72)

class TokenData(BaseModel):
    email: EmailStr