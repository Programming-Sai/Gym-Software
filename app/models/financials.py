from sqlalchemy import (
    DECIMAL,
    Column,
    String,
    ForeignKey,
    Enum,
    TIMESTAMP,
    Integer,
    Boolean,
    JSON,
    Index,
    text,
    Text,
    UniqueConstraint,
)
from uuid import uuid4
from sqlalchemy import func
from app.core.database import Base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression

class SubscriptionTier(Base):
    """Definition of subscription tiers (for users and gyms)"""
    __tablename__ = "subscription_tiers"
    
    tier_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    tier_name = Column(String, nullable=False, unique=True)
    tier_type = Column(
        Enum("user", "gym", name="subscription_tier_types"),
        nullable=False
    )
    price_monthly = Column(DECIMAL(12, 2), nullable=False)
    price_yearly = Column(DECIMAL(12, 2), nullable=True)
    features = Column(JSON, nullable=False, server_default=expression.text("'[]'::jsonb"))
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    duration_days = Column(Integer, nullable=False, default=30)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    users = relationship("User", foreign_keys="User.current_subscription_tier_id", back_populates="subscription_tier")
    


class Subscription(Base):
    __tablename__ = "subscriptions"

    subscription_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    
    tier_id = Column(String, ForeignKey("subscription_tiers.tier_id", ondelete="SET NULL"), nullable=True)
    plan_name = Column(String, nullable=False)
    status = Column(
        Enum("pending", "active", "past_due", "cancelled", name="subscription_statuses"),
        nullable=False,
        server_default="pending",
    )
    provider = Column(String, nullable=False, default="paystack")
    current_period_start = Column(TIMESTAMP, nullable=True)
    current_period_end = Column(TIMESTAMP, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index(
            "ix_subscriptions_user_status_unique",
            "user_id",
            unique=True,
            postgresql_where=text("status IN ('active','pending')")
        ),
    )

    # Relationships
    user = relationship("User")
    tier = relationship("SubscriptionTier", foreign_keys=[tier_id])
    payments = relationship("Payment", back_populates="subscription")

class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    subscription_id = Column(String, ForeignKey("subscriptions.subscription_id", ondelete="SET NULL"), nullable=True)
    
    # For gym payouts, link to gym
    gym_id = Column(String, ForeignKey("gyms.gym_id", ondelete="SET NULL"), nullable=True)

    amount = Column(DECIMAL(12, 2), nullable=False)
    fee = Column(DECIMAL(12, 2), default=0, nullable=False)
    net_amount = Column(DECIMAL(12, 2), nullable=False)  # amount - fee
    status = Column(
        Enum("pending", "succeeded", "failed", "refunded", name="payment_statuses"),
        nullable=False,
        server_default="pending",
    )
    
    payment_type = Column(
        Enum("subscription", "checkin", "product", "other", name="payment_types"),
        nullable=False,
        server_default="subscription"
    )
    
    provider = Column(String, nullable=False, default="paystack")
    provider_payment_id = Column(String, nullable=True)
    receipt_url = Column(String, nullable=True)
    payment_metadata = Column(JSON, server_default=expression.text("'{}'::jsonb"))
    
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    succeeded_at = Column(TIMESTAMP, nullable=True)
    failed_at = Column(TIMESTAMP, nullable=True)
    failure_code = Column(Text, nullable=True)
    raw_provider_payload = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_payments_user_subscription_status", "user_id", "subscription_id", "status"),
        Index("ix_payments_gym_status", "gym_id", "status"),
    )
    
    # Relationships
    user = relationship("User")
    subscription = relationship("Subscription", back_populates="payments")
    gym = relationship("Gym")
    payout = relationship("Payout", uselist=False, back_populates="payment")


class PaymentReconciliationEvent(Base):
    """Audit queue for provider events that don't map to a local payment record."""
    __tablename__ = "payment_reconciliation_events"

    reconciliation_event_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    provider = Column(String, nullable=False, server_default="paystack")
    provider_event = Column(String, nullable=False)
    provider_event_id = Column(String, nullable=True)
    reference = Column(String, nullable=False)
    status = Column(
        Enum("open", "resolved", "ignored", name="reconciliation_event_statuses"),
        nullable=False,
        server_default="open",
    )
    payload = Column(JSON, nullable=False, server_default=expression.text("'{}'::jsonb"))
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_reconciliation_reference_status", "reference", "status"),
        UniqueConstraint(
            "provider",
            "provider_event",
            "reference",
            name="uq_reconciliation_provider_event_reference",
        ),
    )


class Payout(Base):
    """Gym owner payouts"""
    __tablename__ = "payouts"
    
    payout_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    gym_id = Column(String, ForeignKey("gyms.gym_id", ondelete="CASCADE"), nullable=False)
    
    # Link to payment that triggered this payout
    payment_id = Column(
        String, 
        ForeignKey("payments.payment_id", ondelete="SET NULL"), 
        nullable=True
    )
    
    amount = Column(DECIMAL(12, 2), nullable=False)
    status = Column(
        Enum("pending", "processing", "completed", "failed", name="payout_statuses"),
        nullable=False,
        server_default="pending"
    )
    
    scheduled_date = Column(TIMESTAMP, nullable=False)
    processed_date = Column(TIMESTAMP, nullable=True)
    
    provider = Column(String, nullable=False, default="paystack")
    provider_payout_id = Column(String, nullable=True)
    
    failure_reason = Column(Text, nullable=True)
    
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    gym = relationship("Gym", back_populates="payouts")
    payment = relationship("Payment", back_populates="payout")
