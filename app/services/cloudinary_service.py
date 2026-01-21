# app/services/cloudinary_service.py
from typing import Literal
import cloudinary
import cloudinary.uploader
import os

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

def upload_file(
    file,
    folder: str,
    resource_type: Literal["image", "raw"] = "image",
    public_id: str | None = None
):
    """
    resource_type="image" for images
    resource_type="raw" for documents/pdf
    """
    options = {
        "folder": folder,
        "resource_type": resource_type,
        "invalidate": True
    }

    if public_id:
        options["public_id"] = public_id
        options["overwrite"] = True

    return cloudinary.uploader.upload(file, **options)

def delete_file(public_id: str, resource_type: Literal["image", "raw"] = "image"):
    return cloudinary.uploader.destroy(public_id, resource_type=resource_type)
