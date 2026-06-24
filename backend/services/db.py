import logging
from motor.motor_asyncio import AsyncIOMotorClient
from backend.config.settings import settings

logger = logging.getLogger("db-service")

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

db_instance = MongoDB()

async def connect_to_mongo():
    logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL}...")
    db_instance.client = AsyncIOMotorClient(settings.MONGODB_URL)
    db_instance.db = db_instance.client[settings.DATABASE_NAME]
    
    # Initialize indexes
    try:
        # User unique email
        await db_instance.db.users.create_index("email", unique=True)
        # Tenant unique DID
        await db_instance.db.tenants.create_index("did", unique=True, sparse=True)
        # Patient unique phone per clinic
        await db_instance.db.patients.create_index([("clinic_id", 1), ("phone", 1)], unique=True)
        # Call log call ID index
        await db_instance.db.call_logs.create_index("call_id", unique=True)
        # Appointment index by date and clinic
        await db_instance.db.appointments.create_index([("clinic_id", 1), ("appointment_date", 1)])
        logger.info("MongoDB connected and indexes initialized.")
    except Exception as e:
        logger.error(f"Error establishing MongoDB indexes: {e}")

async def close_mongo_connection():
    if db_instance.client:
        db_instance.client.close()
        logger.info("MongoDB connection closed.")

def get_database():
    return db_instance.db
