import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.db import get_db
from backend.routes.auth import get_current_user
from backend.models import PhoneNumber
from backend.utils.helpers import api_response, serialize_model, serialize_models, to_uuid

logger = logging.getLogger("phone-numbers-router")
router = APIRouter(prefix="/phone-numbers", tags=["Phone Numbers"])

MANAGER_ROLES = {"doctor", "admin"}
# Lenient E.164-style check: optional +, leading non-zero digit, 7-16 digits total.
PHONE_RE = re.compile(r"^\+?[1-9]\d{6,15}$")


def _require_manager(current_user: dict):
    if current_user.get("role") not in MANAGER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinic admins can manage phone numbers",
        )


class NumberConnect(BaseModel):
    number: str
    label: Optional[str] = None


class NumberUpdate(BaseModel):
    label: Optional[str] = None
    status: Optional[str] = None


@router.get("/")
async def list_numbers(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    clinic_id = to_uuid(current_user.get("clinic_id"))
    if clinic_id is None:
        return api_response(success=False, message="No clinic associated with user", status_code=400)
    rows = (await db.execute(
        select(PhoneNumber).where(PhoneNumber.clinic_id == clinic_id).order_by(PhoneNumber.created_at.desc())
    )).scalars().all()
    return api_response(success=True, message="Phone numbers fetched", data=serialize_models(rows))


@router.post("/")
async def connect_number(
    payload: NumberConnect,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_manager(current_user)
    clinic_id = to_uuid(current_user.get("clinic_id"))
    if clinic_id is None:
        return api_response(success=False, message="No clinic associated with user", status_code=400)

    number = (payload.number or "").strip().replace(" ", "")
    if not PHONE_RE.match(number):
        return api_response(
            success=False,
            message="Enter a valid phone number in international format (e.g. +14155550100).",
            status_code=400,
        )

    existing = (await db.execute(select(PhoneNumber).where(PhoneNumber.number == number))).scalar_one_or_none()
    if existing:
        return api_response(success=False, message="That number is already connected.", status_code=400)

    pn = PhoneNumber(clinic_id=clinic_id, number=number, label=(payload.label or None), status="active")
    db.add(pn)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return api_response(success=False, message="That number is already connected.", status_code=400)

    return api_response(success=True, message="Phone number connected", data=serialize_model(pn))


@router.put("/{number_id}")
async def update_number(
    number_id: str,
    payload: NumberUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_manager(current_user)
    clinic_id = to_uuid(current_user.get("clinic_id"))
    nid = to_uuid(number_id)
    if nid is None:
        return api_response(success=False, message="Phone number not found", status_code=404)

    pn = (await db.execute(
        select(PhoneNumber).where(PhoneNumber.id == nid, PhoneNumber.clinic_id == clinic_id)
    )).scalar_one_or_none()
    if not pn:
        return api_response(success=False, message="Phone number not found", status_code=404)

    if payload.label is not None:
        pn.label = payload.label or None
    if payload.status is not None:
        if payload.status not in ("active", "inactive"):
            return api_response(success=False, message="Invalid status", status_code=400)
        pn.status = payload.status
    await db.commit()
    return api_response(success=True, message="Phone number updated", data=serialize_model(pn))


@router.delete("/{number_id}")
async def remove_number(
    number_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_manager(current_user)
    clinic_id = to_uuid(current_user.get("clinic_id"))
    nid = to_uuid(number_id)
    if nid is None:
        return api_response(success=False, message="Phone number not found", status_code=404)

    pn = (await db.execute(
        select(PhoneNumber).where(PhoneNumber.id == nid, PhoneNumber.clinic_id == clinic_id)
    )).scalar_one_or_none()
    if not pn:
        return api_response(success=False, message="Phone number not found", status_code=404)

    await db.delete(pn)
    await db.commit()
    return api_response(success=True, message="Phone number removed")
