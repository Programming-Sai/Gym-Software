import logging

from fastapi import APIRouter
from sqlalchemy import text
from pydantic import BaseModel
import firebase_admin

from app.core.database import engine
from app.services.fcm_service import fcm_service

router = APIRouter()
logger = logging.getLogger(__name__)


def test_db_connection():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("DB connection error")
        return False


# Pydantic model for the response
class HealthResponse(BaseModel):
    status: str
    db_connected: bool
    fcm_enabled: bool
    fcm_initialized: bool  # Check if Firebase app exists


@router.get(
    "/",
    tags=["Health"],
    summary="Health Check Endpoint",
    description="Returns the status of the API and database connection.",
    response_model=HealthResponse,
    response_description="Returns JSON with API and DB status"
)
def health():
    """
    Health check endpoint for the API.

    Returns:
        status: "ok" if API and DB are reachable, otherwise "db_error"
        db_connected: boolean indicating DB connection success
        fcm_enabled: boolean indicating if FCM is configured
        fcm_initialized: boolean indicating if Firebase is initialized
    """
    db_status = test_db_connection()
    
    # Check if Firebase is initialized
    fcm_initialized = bool(firebase_admin._apps)
    
    return HealthResponse(
        status="ok" if db_status else "db_error",
        db_connected=db_status,
        fcm_enabled=fcm_service.enabled,
        fcm_initialized=fcm_initialized,
    )
