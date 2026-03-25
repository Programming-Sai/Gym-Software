import enum
from sqlalchemy import Enum as SQLAlchemyEnum


class UserRole(str, enum.Enum):
    GYM_USER = "gym_user"
    GYM_OWNER = "gym_owner"
    DIETICIAN = "dietician"
    ADMIN = "admin"

    def __str__(self):
        return self.value


# SQLAlchemy enum for database columns
user_role_enum = SQLAlchemyEnum(
    UserRole,
    name="user_roles",
    create_type=False, 
    values_callable=lambda obj: [e.value for e in obj]
)


# Document type enum (keep as is)
DocumentTypeEnum = SQLAlchemyEnum(
    "business_license",
    "id",
    "certification",
    "proof_of_ownership",
    "gym_photos",
    "education",
    "other",
    name="document_types",
)