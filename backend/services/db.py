"""
Async Postgres (Supabase) data layer.

Replaces the previous MongoDB (motor) connection. We treat Supabase purely as
hosted Postgres and talk to it with SQLAlchemy 2.0 async + asyncpg.

Connection config is built so it works with Supabase's transaction pooler
(pgbouncer), which does not support cached/named prepared statements:
  - statement_cache_size=0            -> disables asyncpg's prepared-statement cache
  - prepared_statement_cache_size=0   -> disables SQLAlchemy's asyncpg PS cache
  - prepared_statement_name_func      -> unique name per statement
See: https://supabase.com/docs/guides/troubleshooting/using-sqlalchemy-with-supabase-FUqebT

The URL is assembled with SQLAlchemy's URL.create() from individual parts
(DB_USER/DB_PASSWORD/DB_HOST/...) so passwords with special characters (@, #,
:, /) need no URL-encoding. A full DATABASE_URL is also supported and takes
precedence.
"""

import logging
import ssl
import uuid
from urllib.parse import urlsplit, unquote

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)

from backend.config.settings import settings
from backend.models import Base

logger = logging.getLogger("db-service")

# Set during connect_to_db(); stay None until a successful connection so the app
# can still boot (and surface a clear 503) when the DB isn't configured.
engine = None
AsyncSessionLocal = None


def get_sessionmaker():
    """Return the async sessionmaker, or None if the DB isn't connected yet."""
    return AsyncSessionLocal


def _build_url():
    """Build a SQLAlchemy URL for asyncpg, or return None if unconfigured.

    Priority: a full DATABASE_URL (if set) is parsed into parts; otherwise the
    individual DB_* settings are used. Either way URL.create() handles escaping,
    so special characters in the password are safe and need no encoding.
    """
    raw = (settings.DATABASE_URL or "").strip()
    if raw:
        parts = urlsplit(raw)
        return URL.create(
            "postgresql+asyncpg",
            username=unquote(parts.username) if parts.username else None,
            password=unquote(parts.password) if parts.password else None,
            host=parts.hostname,
            port=parts.port,
            database=(parts.path or "").lstrip("/") or "postgres",
        )

    if settings.DB_HOST:
        return URL.create(
            "postgresql+asyncpg",
            username=settings.DB_USER or None,
            password=settings.DB_PASSWORD or None,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME or "postgres",
        )

    return None


def _connect_args(host: str) -> dict:
    """Connect args for the SQLAlchemy asyncpg adapter.

    The adapter pops `prepared_statement_cache_size` and
    `prepared_statement_name_func`; the rest (`statement_cache_size`,
    `server_settings`, `ssl`) go to asyncpg.connect().
    """
    args: dict = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__",
        "server_settings": {"jit": "off"},
    }
    if (host or "").lower() not in ("localhost", "127.0.0.1", ""):
        # Encrypt the connection but skip CA verification. Supabase's pooler
        # chain includes a self-signed root that isn't in the public CA bundle,
        # so full verification fails; this is the libpq `sslmode=require`
        # equivalent and the standard Supabase + asyncpg setup.
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        args["ssl"] = ctx
    return args


async def connect_to_db():
    """Create the async engine + sessionmaker and ensure the schema exists."""
    global engine, AsyncSessionLocal

    url = _build_url()
    if url is None:
        logger.error(
            "Database is not configured. Set DATABASE_URL, or the DB_HOST/"
            "DB_USER/DB_PASSWORD parts, in .env (Supabase connection)."
        )
        return

    try:
        engine = create_async_engine(
            url,
            echo=False,
            pool_pre_ping=True,
            connect_args=_connect_args(url.host),
        )
        AsyncSessionLocal = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        # Idempotently create any missing tables. Existing tables are untouched.
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Connected to Postgres (Supabase) and ensured schema exists.")
    except Exception as e:
        logger.error(f"Failed to connect to Postgres: {e}")
        engine = None
        AsyncSessionLocal = None


async def close_db_connection():
    global engine
    if engine is not None:
        await engine.dispose()
        logger.info("Postgres connection pool disposed.")


async def get_db():
    """FastAPI dependency that yields an AsyncSession per request."""
    if AsyncSessionLocal is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail="Database is not configured. Set the Supabase DB settings in .env.",
        )
    async with AsyncSessionLocal() as session:
        yield session
