import logging
from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from backend.services.db import get_database
from backend.services.auth_service import get_password_hash, verify_password, create_access_token, decode_access_token
from backend.schemas.auth import UserRegister, UserLogin, Token, UserResponse
from backend.utils.helpers import api_response, serialize_doc

logger = logging.getLogger("auth-router")
router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
        
    db = get_database()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise credentials_exception
        
    return serialize_doc(user)

def require_roles(allowed_roles: list):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource"
            )
        return current_user
    return role_checker

@router.post("/register")
async def register(payload: UserRegister):
    db = get_database()
    
    # Check if user already exists
    existing_user = await db.users.find_one({"email": payload.email})
    if existing_user:
        return api_response(success=False, message="Email already registered", status_code=400)
    
    # Create Tenant (Clinic) first
    clinic_id = None
    if payload.role == "doctor" or payload.clinic_name:
        clinic_name = payload.clinic_name or f"{payload.name}'s Clinic"
        clinic_doc = {
            "name": clinic_name,
            "subscription": "free",
            "created_at": datetime.utcnow()
        }
        
        # Omit DID entirely if not provided or empty to satisfy MongoDB sparse unique index constraint
        did_val = payload.did.strip() if payload.did else None
        if did_val:
            clinic_doc["did"] = did_val
            
        tenant_result = await db.tenants.insert_one(clinic_doc)
        clinic_id = str(tenant_result.inserted_id)
        
        if did_val:
            logger.info(f"Registered clinic {clinic_name} with DID {did_val}")
    
    # Hash password
    hashed_pwd = get_password_hash(payload.password)
    
    # Create User doc
    user_doc = {
        "email": payload.email,
        "password_hash": hashed_pwd,
        "name": payload.name,
        "role": payload.role,
        "clinic_id": clinic_id,
        "created_at": datetime.utcnow()
    }
    
    user_result = await db.users.insert_one(user_doc)
    user_id = str(user_result.inserted_id)
    
    # Generate token
    token_data = {"sub": user_id, "role": payload.role, "clinic_id": clinic_id}
    access_token = create_access_token(token_data)
    
    response_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "role": payload.role,
        "name": payload.name,
        "clinic_id": clinic_id
    }
    
    return api_response(success=True, message="Registration successful", data=response_data)

@router.post("/login")
async def login(payload: UserLogin):
    db = get_database()
    
    user = await db.users.find_one({"email": payload.email})
    if not user:
        return api_response(success=False, message="Invalid email or password", status_code=400)
        
    if not verify_password(payload.password, user["password_hash"]):
        return api_response(success=False, message="Invalid email or password", status_code=400)
        
    user_id = str(user["_id"])
    role = user["role"]
    clinic_id = user.get("clinic_id")
    name = user["name"]
    
    # Generate token
    token_data = {"sub": user_id, "role": role, "clinic_id": clinic_id}
    access_token = create_access_token(token_data)
    
    response_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "role": role,
        "name": name,
        "clinic_id": clinic_id
    }
    
    return api_response(success=True, message="Login successful", data=response_data)

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    user_response = {
        "id": current_user["id"],
        "email": current_user["email"],
        "name": current_user["name"],
        "role": current_user["role"],
        "clinic_id": current_user.get("clinic_id")
    }
    return api_response(success=True, message="Current user fetched successfully", data=user_response)
