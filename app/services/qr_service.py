import io
import qrcode
from app.crud.files import MEDIA_PROJECT_FOLDER
from app.services.cloudinary_service import upload_file

def generate_gym_qr(gym_id: str, storage_key: str):
    """
    Generates a random QR code nonce, creates a QR code PNG, uploads it to Cloudinary,
    and returns (qr_nonce, file_id)
    """
    import secrets
    qr_nonce = secrets.token_urlsafe(16)  # random string for QR

    # Encode QR (you could include gym_id + nonce if you like)
    qr_data = qr_nonce  # client will scan and send this to backend
    qr_img = qrcode.make(qr_data)

    # Save to bytes
    buffer = io.BytesIO()
    qr_img.save(buffer, format="PNG")
    buffer.seek(0)

    # Upload to Cloudinary
    upload_kwargs = {
        "file": buffer,
        "folder": f"{MEDIA_PROJECT_FOLDER}/{gym_id}/qr",
        "resource_type": "image",
    }

    # ONLY overwrite if we explicitly have a storage_key
    if storage_key:
        upload_kwargs["public_id"] = storage_key

    result = upload_file(**upload_kwargs)

    return qr_nonce, result["public_id"], result["secure_url"]
