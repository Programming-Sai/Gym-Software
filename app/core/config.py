import json
from pydantic import field_validator
from pydantic_settings  import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    DATABASE_URL: str

    SECRET_KEY: str
    JWT_SECRET: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    OTP_LENGTH: int = 6
    OTP_EXPIRE_MINUTES: int = 10

    CLOUDINARY_CLOUD_NAME: str 
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str 
    CLOUDINARY_URL: str | None = None

    FACE_API_SECRET: str 
    FACE_API_KEY: str 

    PAYSTACK_SECRET_KEY: str
    PAYSTACK_PUBLIC_KEY: str

    ALLOWED_CALLBACK_DOMAINS: list[str] = []

    ENVIRONMENT: Literal["dev", "prod"] = "dev"

    @field_validator("ALLOWED_CALLBACK_DOMAINS", mode="before")
    @classmethod
    def parse_domains(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    class Config:
        env_file = ".env"

settings = Settings()
