from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str
    role: str = Field("doctor", description="doctor, admin, receptionist")
    clinic_name: Optional[str] = None
    did: Optional[str] = None  # Mapping phone number / DID
    industry: Optional[str] = None  # Vertical key (clinic, real_estate, ...) for the starter template

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    name: str
    clinic_id: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: str
    clinic_id: Optional[str] = None
