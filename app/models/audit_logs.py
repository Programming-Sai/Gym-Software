from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DECIMAL,
    ForeignKey,
    JSON,
    String,
    TEXT,
    TIMESTAMP,
    Index,
)
from sqlalchemy import func
from sqlalchemy.sql import expression

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_log_id = Column(String, primary_key=True, default=lambda: str(uuid4()))

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Classification
    category = Column(String(length=16), nullable=False)  # "money" | "crud"
    action = Column(String(length=96), nullable=False)  # e.g. "payment.succeeded", "payout.processed"

    # What was affected
    entity_type = Column(String(length=32), nullable=False)  # "payment" | "payout" | "user" | "gym"
    entity_id = Column(String, nullable=True)

    # Actor (who performed the action)
    actor_user_id = Column(String, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    actor_role = Column(String(length=32), nullable=True)
    actor_ip = Column(String(length=64), nullable=True)
    user_agent = Column(String(length=256), nullable=True)
    request_id = Column(String(length=64), nullable=True)

    # Money attribution (who paid who; approvals; direction is inferred from action/entity)
    amount = Column(DECIMAL(12, 2), nullable=True)
    currency = Column(String(length=8), nullable=True)
    provider = Column(String(length=32), nullable=True)
    provider_reference = Column(String(length=128), nullable=True)

    payer_user_id = Column(String, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    payee_user_id = Column(String, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    payee_gym_id = Column(String, ForeignKey("gyms.gym_id", ondelete="SET NULL"), nullable=True)

    initiated_by_user_id = Column(String, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    approved_by_user_id = Column(String, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)

    success = Column(Boolean, nullable=False, server_default=expression.true())
    error_message = Column(TEXT, nullable=True)

    audit_metadata = Column(
        "metadata",
        JSON,
        nullable=False,
        server_default=expression.text("'{}'::jsonb"),
    )

    __table_args__ = (
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_category_action", "category", "action"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_actor", "actor_user_id", "created_at"),
        Index("ix_audit_logs_request_id", "request_id"),
        Index("ix_audit_logs_money", "payer_user_id", "payee_gym_id", "created_at"),
    )
