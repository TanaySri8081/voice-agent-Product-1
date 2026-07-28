import asyncio
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import settings
from backend.services.db import get_db
from backend.services.limiter import limiter
from backend.services.auth_service import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
    generate_token,
    hash_token,
)
from backend.services.email import send_email
from backend.services.industry_templates import get_template
from backend.models import User, Tenant, PasswordResetToken, PhoneNumber
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


def is_superadmin(email: str) -> bool:
    """True if the email is in the platform SUPERADMIN_EMAILS allowlist."""
    allow = [e.strip().lower() for e in (settings.SUPERADMIN_EMAILS or "").split(",") if e.strip()]
    return bool(email) and email.strip().lower() in allow


async def require_superadmin(current_user: dict = Depends(get_current_user)):
    """Dependency that restricts a route to platform super-admins."""
    if not is_superadmin(current_user.get("email", "")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )
    return current_user


@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, payload: UserRegister, db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        return api_response(success=False, message="Email already registered", status_code=400)

    # Create Tenant (the client's business) first, when applicable.
    clinic_id = None
    if payload.role == "doctor" or payload.clinic_name:
        clinic_name = payload.clinic_name or f"{payload.name}'s Business"
        did_val = payload.did.strip() if payload.did else None
        # Seed the agent with a vertical-specific starter prompt/greeting from
        # the chosen industry template (falls back to the generic defaults when
        # no/unknown industry is given). The client can edit these in Settings.
        tmpl = get_template(payload.industry)
        tenant = Tenant(
            name=clinic_name,
            subscription="free",
            did=did_val or None,
            industry=(payload.industry.strip().lower() if tmpl else None),
            system_prompt=(tmpl["system_prompt"] if tmpl else None),
            initial_greeting=(tmpl["initial_greeting"] if tmpl else None),
        )
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
            pn = PhoneNumber(clinic_id=clinic_id, number=did_val, label="Primary DID", status="active")
            db.add(pn)

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
        "id": user_id,
        "email": payload.email,
        "role": payload.role,
        "name": payload.name,
        "clinic_id": clinic_id_str,
        "is_superadmin": is_superadmin(payload.email),
    }
    return api_response(success=True, message="Registration successful", data=response_data)


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, payload: UserLogin, db: AsyncSession = Depends(get_db)):
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
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "name": user.name,
        "clinic_id": clinic_id_str,
        "is_superadmin": is_superadmin(user.email),
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
        "is_superadmin": is_superadmin(current_user["email"]),
    }
    return api_response(success=True, message="Current user fetched successfully", data=user_response)


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


class ProfileUpdate(BaseModel):
    name: str = Field(..., min_length=1)


class ForgotPassword(BaseModel):
    email: EmailStr


class ResetPassword(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)


@router.put("/profile")
async def update_profile(
    payload: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.id == to_uuid(current_user["id"])))).scalar_one_or_none()
    if not user:
        return api_response(success=False, message="User not found", status_code=404)
    user.name = payload.name.strip()
    await db.commit()
    return api_response(success=True, message="Profile updated", data={"name": user.name})


@router.post("/change-password")
async def change_password(
    payload: ChangePassword,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.id == to_uuid(current_user["id"])))).scalar_one_or_none()
    if not user:
        return api_response(success=False, message="User not found", status_code=404)
    if not verify_password(payload.current_password, user.password_hash):
        return api_response(success=False, message="Current password is incorrect", status_code=400)
    user.password_hash = get_password_hash(payload.new_password)
    await db.commit()
    return api_response(success=True, message="Password changed successfully")


@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(request: Request, payload: ForgotPassword, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if user:
        raw = generate_token()
        db.add(PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            purpose="reset",
            expires_at=datetime.utcnow() + timedelta(hours=1),
        ))
        await db.commit()
        link = f"{settings.APP_BASE_URL}/reset-password?token={raw}"
        await asyncio.to_thread(
            send_email,
            user.email,
            "Reset your VoxPilot password",
            f"Use this link to reset your password (valid for 1 hour):\n\n{link}\n\n"
            "If you didn't request this, you can safely ignore this email.",
        )
    # Anti-enumeration: identical response whether or not the email exists.
    return api_response(success=True, message="If that email is registered, a reset link has been sent.")


@router.post("/reset-password")
@limiter.limit("10/minute")
async def reset_password(request: Request, payload: ResetPassword, db: AsyncSession = Depends(get_db)):
    token_hash = hash_token(payload.token)
    row = (await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )).scalar_one_or_none()
    if not row or row.used_at is not None or row.expires_at < datetime.utcnow():
        return api_response(success=False, message="This link is invalid or has expired.", status_code=400)
    user = (await db.execute(select(User).where(User.id == row.user_id))).scalar_one_or_none()
    if not user:
        return api_response(success=False, message="This link is invalid or has expired.", status_code=400)
    user.password_hash = get_password_hash(payload.new_password)
    row.used_at = datetime.utcnow()
    await db.commit()
    return api_response(success=True, message="Password set successfully. You can now sign in.")
