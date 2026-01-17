from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.v1.auth import router as auth_router

app = FastAPI(title="Gym Software API", version="1.0")

base = "/api/v1"

app.include_router(health_router, prefix=base+"/health")
app.include_router(auth_router, prefix=base+"/auth")
