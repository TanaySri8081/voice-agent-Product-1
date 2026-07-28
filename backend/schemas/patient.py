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
    patient_name: str
    appointment_at: Optional[datetime] = None   # structured start (naive local wall-time)
    duration_min: int = 30
    phone: Optional[str] = None                  # customer phone for WhatsApp
    reason: Optional[str] = None
    patient_id: Optional[str] = "manual"
    status: str = "scheduled"  # scheduled, completed, cancelled, rescheduled
    appointment_date: Optional[str] = None       # display string; derived from appointment_at if omitted

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
