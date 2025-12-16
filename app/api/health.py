from fastapi import APIRouter
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
from app.core.database import DATABASE_URL 
from pydantic import BaseModel

load_dotenv()

router = APIRouter()

# DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/gymdb")

def test_db_connection():
    try:
        engine = create_engine(DATABASE_URL)
        conn = engine.connect()
        conn.close()
        return True
    except Exception as e:
        print(f"DB connection error: {e}")
        return False

# Pydantic model for the response
class HealthResponse(BaseModel):
    status: str
    db_connected: bool

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
    """
    db_status = test_db_connection()
    return HealthResponse(
        status="ok" if db_status else "db_error",
        db_connected=db_status
    )
    