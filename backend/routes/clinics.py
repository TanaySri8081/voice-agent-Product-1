from bson import ObjectId
from fastapi import APIRouter, Depends
from backend.services.db import get_database
from backend.routes.auth import get_current_user
from backend.utils.helpers import api_response, serialize_doc
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/clinics", tags=["Clinic Profile"])

class ClinicSettingsUpdate(BaseModel):
    name: Optional[str] = None
    did: Optional[str] = None
    system_prompt: Optional[str] = None
    initial_greeting: Optional[str] = None
    transfer_number: Optional[str] = None

@router.get("/settings")
async def get_settings(current_user: dict = Depends(get_current_user)):
    db = get_database()
    clinic_id = current_user.get("clinic_id")
    if not clinic_id:
        return api_response(success=False, message="No clinic associated with user", status_code=400)
        
    tenant = await db.tenants.find_one({"_id": ObjectId(clinic_id)})
    if not tenant:
        return api_response(success=False, message="Clinic settings not found", status_code=404)
        
    return api_response(
        success=True,
        message="Clinic settings fetched successfully",
        data=serialize_doc(tenant)
    )

@router.put("/settings")
async def update_settings(payload: ClinicSettingsUpdate, current_user: dict = Depends(get_current_user)):
    db = get_database()
    clinic_id = current_user.get("clinic_id")
    if not clinic_id:
        return api_response(success=False, message="No clinic associated with user", status_code=400)
        
    update_data = payload.dict(exclude_unset=True)
    if not update_data:
        return api_response(success=False, message="No settings data provided for update", status_code=400)
        
    await db.tenants.update_one({"_id": ObjectId(clinic_id)}, {"$set": update_data})
    
    updated = await db.tenants.find_one({"_id": ObjectId(clinic_id)})
    return api_response(
        success=True,
        message="Clinic settings updated successfully",
        data=serialize_doc(updated)
    )
