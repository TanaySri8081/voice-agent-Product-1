-- VoxPilot AI — Supabase Postgres schema
--
-- This file is OPTIONAL. The backend calls SQLAlchemy's create_all() on startup,
-- which creates any missing tables automatically. Use this script if you prefer
-- to provision the schema yourself via the Supabase SQL editor.
--
-- Multi-tenancy is enforced in the application layer (every query filters by
-- clinic_id) using the backend's own JWT auth. The app connects with the
-- Postgres role, so Row Level Security is intentionally NOT used here. Do not
-- expose these tables through the Supabase client/anon key without adding RLS.

create extension if not exists "pgcrypto";  -- provides gen_random_uuid()

-- ===== tenants (clinics) =====
create table if not exists tenants (
    id               uuid primary key default gen_random_uuid(),
    name             varchar(255) not null,
    subscription     varchar(50)  not null default 'free',
    did              varchar(50)  unique,
    system_prompt    text,
    initial_greeting text,
    knowledge_base   text,
    voice            varchar(100),
    language         varchar(20),
    llm_model        varchar(100),
    transfer_number  varchar(50),
    created_at       timestamp    not null default (now() at time zone 'utc')
);

-- ===== users =====
create table if not exists users (
    id            uuid primary key default gen_random_uuid(),
    email         varchar(255) not null unique,
    password_hash varchar(255) not null,
    name          varchar(255) not null,
    role          varchar(50)  not null default 'doctor',
    clinic_id     uuid references tenants(id) on delete set null,
    created_at    timestamp    not null default (now() at time zone 'utc')
);
create index if not exists ix_users_clinic_id on users(clinic_id);

-- ===== patients =====
create table if not exists patients (
    id              uuid primary key default gen_random_uuid(),
    clinic_id       uuid not null references tenants(id) on delete cascade,
    name            varchar(255) not null,
    phone           varchar(50)  not null,
    email           varchar(255),
    age             integer,
    gender          varchar(20),
    history         jsonb not null default '[]'::jsonb,
    follow_up_notes text,
    created_at      timestamp not null default (now() at time zone 'utc'),
    constraint uq_patient_clinic_phone unique (clinic_id, phone)
);
create index if not exists ix_patients_clinic_id on patients(clinic_id);

-- ===== appointments =====
create table if not exists appointments (
    id               uuid primary key default gen_random_uuid(),
    clinic_id        uuid not null references tenants(id) on delete cascade,
    patient_id       varchar(64),         -- patient uuid (as text) or 'new'
    patient_name     varchar(255) not null,
    appointment_date text not null,       -- ISO or human-readable string
    reason           text,
    status           varchar(50) not null default 'scheduled',
    created_at       timestamp not null default (now() at time zone 'utc')
);
create index if not exists ix_appointments_clinic_id on appointments(clinic_id);
create index if not exists ix_appointments_status on appointments(status);

-- ===== call_logs =====
create table if not exists call_logs (
    id            uuid primary key default gen_random_uuid(),
    call_id       varchar(255) not null unique,
    clinic_id     uuid references tenants(id) on delete set null,
    caller_name   varchar(255),
    phone         varchar(50),
    direction     varchar(20),
    duration      integer not null default 0,
    status        varchar(50),
    transcript    jsonb not null default '[]'::jsonb,
    recording_url text,
    created_at    timestamp not null default (now() at time zone 'utc')
);
create index if not exists ix_call_logs_clinic_id on call_logs(clinic_id);

-- ===== password_reset_tokens (password reset + team invite links) =====
create table if not exists password_reset_tokens (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references users(id) on delete cascade,
    token_hash  varchar(64) not null unique,   -- sha256 hex of the token
    purpose     varchar(20) not null default 'reset',  -- reset | invite
    expires_at  timestamp not null,
    used_at     timestamp,
    created_at  timestamp not null default (now() at time zone 'utc')
);
create index if not exists ix_password_reset_tokens_user_id on password_reset_tokens(user_id);

-- ===== phone_numbers (inbound DIDs connected by each clinic) =====
create table if not exists phone_numbers (
    id          uuid primary key default gen_random_uuid(),
    clinic_id   uuid not null references tenants(id) on delete cascade,
    number      varchar(32) not null unique,
    label       varchar(100),
    status      varchar(20) not null default 'active',  -- active | inactive
    created_at  timestamp not null default (now() at time zone 'utc')
);
create index if not exists ix_phone_numbers_clinic_id on phone_numbers(clinic_id);
