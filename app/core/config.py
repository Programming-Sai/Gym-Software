from pydantic_settings  import BaseSettings

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

    class Config:
        env_file = ".env"

settings = Settings()
