from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from backend.services.db import get_database
from backend.routes.auth import get_current_user
from backend.schemas.patient import PatientCreate
from backend.utils.helpers import api_response, serialize_doc, serialize_docs

router = APIRouter(prefix="/patients", tags=["Patients CRM"])

@router.get("/")
async def list_patients(current_user: dict = Depends(get_current_user)):
    db = get_database()
    clinic_id = current_user.get("clinic_id")
    if not clinic_id:
        return api_response(success=False, message="No clinic associated with user", status_code=400)
        
    patients = await db.patients.find({"clinic_id": clinic_id}).to_list(200)
    return api_response(
        success=True,
        message="Patients fetched successfully",
        data=serialize_docs(patients)
    )

@router.post("/")
async def create_patient(payload: PatientCreate, current_user: dict = Depends(get_current_user)):
    db = get_database()
    clinic_id = current_user.get("clinic_id")
    if not clinic_id:
        return api_response(success=False, message="No clinic associated with user", status_code=400)
        
    # Check if phone number is already registered for this clinic
    existing = await db.patients.find_one({"phone": payload.phone, "clinic_id": clinic_id})
    if existing:
        return api_response(success=False, message="Patient with this phone number already exists", status_code=400)
        
    patient_doc = payload.dict()
    patient_doc["clinic_id"] = clinic_id
    patient_doc["created_at"] = datetime.utcnow()
    
    result = await db.patients.insert_one(patient_doc)
    patient_doc["id"] = str(result.inserted_id)
    del patient_doc["_id"]
    
    return api_response(
        success=True,
        message="Patient created successfully",
        data=patient_doc
    )

@router.get("/{patient_id}")
async def get_patient(patient_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    clinic_id = current_user.get("clinic_id")
    
    patient = await db.patients.find_one({"_id": ObjectId(patient_id), "clinic_id": clinic_id})
    if not patient:
        return api_response(success=False, message="Patient not found", status_code=404)
        
    return api_response(
        success=True,
        message="Patient fetched successfully",
        data=serialize_doc(patient)
    )

@router.put("/{patient_id}")
async def update_patient(patient_id: str, payload: PatientCreate, current_user: dict = Depends(get_current_user)):
    db = get_database()
    clinic_id = current_user.get("clinic_id")
    
    existing = await db.patients.find_one({"_id": ObjectId(patient_id), "clinic_id": clinic_id})
    if not existing:
        return api_response(success=False, message="Patient not found", status_code=404)
        
    update_data = payload.dict(exclude_unset=True)
    await db.patients.update_one({"_id": ObjectId(patient_id)}, {"$set": update_data})
    
    updated_patient = await db.patients.find_one({"_id": ObjectId(patient_id)})
    return api_response(
        success=True,
        message="Patient updated successfully",
        data=serialize_doc(updated_patient)
    )

@router.delete("/{patient_id}")
async def delete_patient(patient_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    clinic_id = current_user.get("clinic_id")
    
    existing = await db.patients.find_one({"_id": ObjectId(patient_id), "clinic_id": clinic_id})
    if not existing:
        return api_response(success=False, message="Patient not found", status_code=404)
        
    await db.patients.delete_one({"_id": ObjectId(patient_id)})
    return api_response(
        success=True,
        message="Patient deleted successfully"
    )
