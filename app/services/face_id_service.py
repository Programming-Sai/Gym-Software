# app/services/face_id_service.py
import requests
from app.core.config import settings

FACEPP_COMPARE_URL = "https://api-us.faceplusplus.com/facepp/v3/compare"

def compare_faces(stored_image_url: str, image_base64_2: str) -> float:
    """
    Returns similarity score.
    Raises exception on failure.
    """
    print("\n\n\n\n", settings.FACE_API_KEY)
    print(settings.FACE_API_SECRET, "\n\n\n\n")

    payload = {
        "api_key": settings.FACE_API_KEY,
        "api_secret": settings.FACE_API_SECRET,
        "image_url1": stored_image_url,
        "image_base64_2": image_base64_2,
    }

    response = requests.post(FACEPP_COMPARE_URL, data=payload, timeout=10)
    response.raise_for_status()

    data = response.json()

    if "confidence" not in data:
        raise ValueError("Invalid Face++ response")

    return float(data["confidence"])


