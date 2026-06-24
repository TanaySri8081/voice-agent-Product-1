from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class PatientBase(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    history: List[str] = Field(default_factory=list)
    follow_up_notes: Optional[str] = None

class PatientCreate(PatientBase):
    pass

class PatientResponse(PatientBase):
    id: str
    clinic_id: str
    created_at: datetime

class AppointmentBase(BaseModel):
    patient_id: str
    patient_name: str
    appointment_date: str  # ISO Format or human string
    reason: Optional[str] = None
    status: str = "scheduled"  # scheduled, completed, cancelled, rescheduled

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentResponse(AppointmentBase):
    id: str
    clinic_id: str
    created_at: datetime

class CallLogResponse(BaseModel):
    id: str
    call_id: str
    clinic_id: str
    caller_name: str
    phone: str
    direction: str  # inbound, outbound
    duration: int  # in seconds
    status: str  # completed, failed, busy, no-answer
    transcript: List[dict]  # list of message dicts (role, content)
    recording_url: Optional[str] = None
    created_at: datetime
