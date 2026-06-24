from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status, Query
from backend.services.db import get_database
from backend.routes.auth import get_current_user
from backend.schemas.patient import AppointmentCreate
from backend.utils.helpers import api_response, serialize_doc, serialize_docs

router = APIRouter(prefix="/appointments", tags=["Appointments"])

@router.get("/")
async def list_appointments(current_user: dict = Depends(get_current_user)):
    db = get_database()
    clinic_id = current_user.get("clinic_id")
    if not clinic_id:
        return api_response(success=False, message="No clinic associated with user", status_code=400)
        
    appointments = await db.appointments.find({"clinic_id": clinic_id}).sort("appointment_date", 1).to_list(200)
    return api_response(
        success=True,
        message="Appointments fetched successfully",
        data=serialize_docs(appointments)
    )

@router.post("/")
async def create_appointment(payload: AppointmentCreate, current_user: dict = Depends(get_current_user)):
    db = get_database()
    clinic_id = current_user.get("clinic_id")
    if not clinic_id:
        return api_response(success=False, message="No clinic associated with user", status_code=400)
        
    appointment_doc = payload.dict()
    appointment_doc["clinic_id"] = clinic_id
    appointment_doc["created_at"] = datetime.utcnow()
    
    result = await db.appointments.insert_one(appointment_doc)
    appointment_doc["id"] = str(result.inserted_id)
    del appointment_doc["_id"]
    
    return api_response(
        success=True,
        message="Appointment created successfully",
        data=appointment_doc
    )

@router.put("/{appointment_id}")
async def update_appointment(
    appointment_id: str,
    payload: AppointmentCreate,
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    clinic_id = current_user.get("clinic_id")
    
    existing = await db.appointments.find_one({"_id": ObjectId(appointment_id), "clinic_id": clinic_id})
    if not existing:
        return api_response(success=False, message="Appointment not found", status_code=404)
        
    update_data = payload.dict(exclude_unset=True)
    await db.appointments.update_one({"_id": ObjectId(appointment_id)}, {"$set": update_data})
    
    updated = await db.appointments.find_one({"_id": ObjectId(appointment_id)})
    return api_response(
        success=True,
        message="Appointment updated successfully",
        data=serialize_doc(updated)
    )

@router.delete("/{appointment_id}")
async def cancel_appointment(appointment_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    clinic_id = current_user.get("clinic_id")
    
    existing = await db.appointments.find_one({"_id": ObjectId(appointment_id), "clinic_id": clinic_id})
    if not existing:
        return api_response(success=False, message="Appointment not found", status_code=404)
        
    await db.appointments.update_one(
        {"_id": ObjectId(appointment_id)},
        {"$set": {"status": "cancelled"}}
    )
    
    return api_response(
        success=True,
        message="Appointment cancelled successfully"
    )
