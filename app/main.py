from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.gyms import router as gym_router
from app.api.v1.users import router as user_router

app = FastAPI(title="Gym Software API", version="1.0")

base = "/api/v1"

app.include_router(health_router, prefix=base+"/health")
app.include_router(auth_router, prefix=base+"/auth")
app.include_router(gym_router, prefix=base+"/gyms")
app.include_router(user_router, prefix=base+"/users")