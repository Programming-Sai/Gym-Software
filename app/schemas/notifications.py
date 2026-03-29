

from typing import Optional

from pydantic import BaseModel


class DeviceRegistrationRequest(BaseModel):
    fcm_token: str
    device_info: Optional[str] = None


class DeviceRegistrationResponse(BaseModel):
    status: str
    message: str
