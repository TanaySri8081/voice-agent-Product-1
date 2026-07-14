"""
SQLAlchemy ORM models for the VoxPilot backend (Supabase Postgres).

These replace the previous MongoDB collections:
  tenants (clinics), users, patients, appointments, call_logs.

Notes:
- Primary keys are UUIDs (generated client-side via uuid4 so they work
  identically against any Postgres instance, including the Supabase pooler).
- `tenants.did` is UNIQUE but nullable; Postgres treats NULLs as distinct, so
  this mirrors the previous Mongo "sparse unique" index (many clinics may have
  no DID, but a present DID must be unique).
- `patients.history` and `call_logs.transcript` use JSONB (previously Mongo
  array fields). `transcript` holds a list of {"role", "content"} dicts.
- `appointments.patient_id` is stored as text (not a FK) because the AI tool
  flow may record "new"/unknown patients that have no patients row yet.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    String,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, mapped_column


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = mapped_column(String(255), nullable=False)
    subscription = mapped_column(String(50), nullable=False, default="free")
    did = mapped_column(String(50), nullable=True, unique=True)
    system_prompt = mapped_column(Text, nullable=True)
    initial_greeting = mapped_column(Text, nullable=True)
    knowledge_base = mapped_column(Text, nullable=True)
    voice = mapped_column(String(100), nullable=True)
    language = mapped_column(String(20), nullable=True)
    llm_model = mapped_column(String(100), nullable=True)
    transfer_number = mapped_column(String(50), nullable=True)
    created_at = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = mapped_column(String(255), nullable=False, unique=True)
    password_hash = mapped_column(String(255), nullable=False)
    name = mapped_column(String(255), nullable=False)
    role = mapped_column(String(50), nullable=False, default="doctor")
    clinic_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class Patient(Base):
    __tablename__ = "patients"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = mapped_column(String(255), nullable=False)
    phone = mapped_column(String(50), nullable=False)
    email = mapped_column(String(255), nullable=True)
    age = mapped_column(Integer, nullable=True)
    gender = mapped_column(String(20), nullable=True)
    history = mapped_column(JSONB, nullable=False, default=list)
    follow_up_notes = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("clinic_id", "phone", name="uq_patient_clinic_phone"),
    )


class Appointment(Base):
    __tablename__ = "appointments"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Stored as text: may be a patient UUID string or "new" for unknown callers.
    patient_id = mapped_column(String(64), nullable=True)
    patient_name = mapped_column(String(255), nullable=False)
    # Kept as text to preserve existing ISO/human-string semantics.
    appointment_date = mapped_column(Text, nullable=False)
    reason = mapped_column(Text, nullable=True)
    status = mapped_column(String(50), nullable=False, default="scheduled", index=True)
    created_at = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class CallLog(Base):
    __tablename__ = "call_logs"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = mapped_column(String(255), nullable=False, unique=True)
    clinic_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    caller_name = mapped_column(String(255), nullable=True)
    phone = mapped_column(String(50), nullable=True)
    direction = mapped_column(String(20), nullable=True)
    duration = mapped_column(Integer, nullable=False, default=0)
    status = mapped_column(String(50), nullable=True)
    transcript = mapped_column(JSONB, nullable=False, default=list)
    recording_url = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Only the SHA-256 hash of the token is stored, never the token itself.
    token_hash = mapped_column(String(64), nullable=False, unique=True)
    purpose = mapped_column(String(20), nullable=False, default="reset")  # reset | invite
    expires_at = mapped_column(DateTime, nullable=False)
    used_at = mapped_column(DateTime, nullable=True)
    created_at = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class PhoneNumber(Base):
    __tablename__ = "phone_numbers"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    number = mapped_column(String(32), nullable=False, unique=True)
    label = mapped_column(String(100), nullable=True)
    status = mapped_column(String(20), nullable=False, default="active")  # active | inactive
    created_at = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


__all__ = ["Base", "Tenant", "User", "Patient", "Appointment", "CallLog", "PasswordResetToken", "PhoneNumber"]
