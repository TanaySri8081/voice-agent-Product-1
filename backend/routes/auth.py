import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.db import get_db
from backend.services.auth_service import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
)
from backend.models import User, Tenant
from backend.schemas.auth import UserRegister, UserLogin
from backend.utils.helpers import api_response, serialize_model, to_uuid

logger = logging.getLogger("auth-router")
router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id = to_uuid(payload.get("sub"))
    if user_id is None:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    return serialize_model(user)


def require_roles(allowed_roles: list):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource",
            )
        return current_user
    return role_checker


@router.post("/register")
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        return api_response(success=False, message="Email already registered", status_code=400)

    # Create Tenant (Clinic) first, when applicable
    clinic_id = None
    if payload.role == "doctor" or payload.clinic_name:
        clinic_name = payload.clinic_name or f"{payload.name}'s Clinic"
        did_val = payload.did.strip() if payload.did else None
        tenant = Tenant(name=clinic_name, subscription="free", did=did_val or None)
        db.add(tenant)
        try:
            await db.flush()  # assigns tenant.id
        except IntegrityError:
            await db.rollback()
            return api_response(
                success=False,
                message="That clinic phone number (DID) is already registered",
                status_code=400,
            )
        clinic_id = tenant.id
        if did_val:
            logger.info(f"Registered clinic {clinic_name} with DID {did_val}")

    # Create the user
    user = User(
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        name=payload.name,
        role=payload.role,
        clinic_id=clinic_id,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return api_response(success=False, message="Email already registered", status_code=400)

    user_id = str(user.id)
    clinic_id_str = str(clinic_id) if clinic_id else None

    token_data = {"sub": user_id, "role": payload.role, "clinic_id": clinic_id_str}
    access_token = create_access_token(token_data)

    response_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "role": payload.role,
        "name": payload.name,
        "clinic_id": clinic_id_str,
    }
    return api_response(success=True, message="Registration successful", data=response_data)


@router.post("/login")
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user:
        return api_response(success=False, message="Invalid email or password", status_code=400)

    if not verify_password(payload.password, user.password_hash):
        return api_response(success=False, message="Invalid email or password", status_code=400)

    clinic_id_str = str(user.clinic_id) if user.clinic_id else None
    token_data = {"sub": str(user.id), "role": user.role, "clinic_id": clinic_id_str}
    access_token = create_access_token(token_data)

    response_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "name": user.name,
        "clinic_id": clinic_id_str,
    }
    return api_response(success=True, message="Login successful", data=response_data)


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    user_response = {
        "id": current_user["id"],
        "email": current_user["email"],
        "name": current_user["name"],
        "role": current_user["role"],
        "clinic_id": current_user.get("clinic_id"),
    }
    return api_response(success=True, message="Current user fetched successfully", data=user_response)
