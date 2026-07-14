import asyncio
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import settings
from backend.services.db import get_db
from backend.services.auth_service import get_password_hash, generate_token, hash_token
from backend.services.email import send_email
from backend.routes.auth import get_current_user
from backend.models import User, PasswordResetToken
from backend.utils.helpers import api_response, to_uuid

logger = logging.getLogger("team-router")
router = APIRouter(prefix="/team", tags=["Team"])

MANAGER_ROLES = {"doctor", "admin"}
VALID_ROLES = {"admin", "receptionist", "doctor"}


async def require_manager(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in MANAGER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinic admins can manage the team",
        )
    if not current_user.get("clinic_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No clinic associated with user",
        )
    return current_user


class InviteMember(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1)
    role: str = Field("receptionist")


class RoleUpdate(BaseModel):
    role: str


def _serialize_user(u: User) -> dict:
    # Deliberately excludes password_hash.
    return {
        "id": str(u.id),
        "email": u.email,
        "name": u.name,
        "role": u.role,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


@router.get("/")
async def list_team(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    clinic_id = to_uuid(current_user.get("clinic_id"))
    if clinic_id is None:
        return api_response(success=False, message="No clinic associated with user", status_code=400)
    rows = (await db.execute(select(User).where(User.clinic_id == clinic_id))).scalars().all()
    return api_response(success=True, message="Team fetched", data=[_serialize_user(u) for u in rows])


@router.post("/")
async def invite_member(
    payload: InviteMember,
    current_user: dict = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    role = payload.role if payload.role in VALID_ROLES else "receptionist"
    clinic_id = to_uuid(current_user.get("clinic_id"))

    existing = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if existing:
        return api_response(success=False, message="A user with that email already exists", status_code=400)

    # Create the teammate with an unusable random password; they set their own
    # password through the invite link.
    user = User(
        email=payload.email,
        password_hash=get_password_hash(generate_token()),
        name=payload.name.strip(),
        role=role,
        clinic_id=clinic_id,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return api_response(success=False, message="A user with that email already exists", status_code=400)

    raw = generate_token()
    db.add(PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(raw),
        purpose="invite",
        expires_at=datetime.utcnow() + timedelta(days=7),
    ))
    await db.commit()

    link = f"{settings.APP_BASE_URL}/reset-password?token={raw}"
    await asyncio.to_thread(
        send_email,
        payload.email,
        "You've been invited to VoxPilot",
        f"You've been added to a VoxPilot clinic. Set your password to get started "
        f"(link valid for 7 days):\n\n{link}",
    )
    # Return the link too, so an admin can share it directly when SMTP is unset.
    return api_response(
        success=True,
        message="Team member invited",
        data={"invite_link": link, "user": _serialize_user(user)},
    )


@router.put("/{user_id}/role")
async def update_role(
    user_id: str,
    payload: RoleUpdate,
    current_user: dict = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    if payload.role not in VALID_ROLES:
        return api_response(success=False, message="Invalid role", status_code=400)
    clinic_id = to_uuid(current_user.get("clinic_id"))
    uid = to_uuid(user_id)
    if uid is None:
        return api_response(success=False, message="User not found", status_code=404)
    user = (await db.execute(
        select(User).where(User.id == uid, User.clinic_id == clinic_id)
    )).scalar_one_or_none()
    if not user:
        return api_response(success=False, message="User not found", status_code=404)
    user.role = payload.role
    await db.commit()
    return api_response(success=True, message="Role updated", data=_serialize_user(user))


@router.delete("/{user_id}")
async def remove_member(
    user_id: str,
    current_user: dict = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    clinic_id = to_uuid(current_user.get("clinic_id"))
    uid = to_uuid(user_id)
    if uid is None:
        return api_response(success=False, message="User not found", status_code=404)
    if str(uid) == str(current_user.get("id")):
        return api_response(success=False, message="You can't remove yourself", status_code=400)
    user = (await db.execute(
        select(User).where(User.id == uid, User.clinic_id == clinic_id)
    )).scalar_one_or_none()
    if not user:
        return api_response(success=False, message="User not found", status_code=404)
    await db.delete(user)
    await db.commit()
    return api_response(success=True, message="Team member removed")
