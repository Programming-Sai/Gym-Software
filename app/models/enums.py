# app/models/enums.py
from sqlalchemy import Enum

DocumentTypeEnum = Enum(
    "business_license",
    "id",
    "certification",
    "proof_of_ownership",
    "gym_photos",
    "education",
    "other",
    name="document_types",
)
