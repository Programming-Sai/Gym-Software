from sqlalchemy import DECIMAL, Column, String, ForeignKey, Enum, TIMESTAMP, Integer, Boolean, JSON, Index, Text
from uuid import uuid4
from sqlalchemy import func
from app.core.database import Base
from sqlalchemy.orm import relationship

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
    features = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    users = relationship("User", foreign_keys="User.current_subscription_tier_id", back_populates="subscription_tier")
    

class Subscription(Base):
    __tablename__ = "subscriptions"

    subscription_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    
    # Reference to subscription tier definition
    tier_id = Column(
        String, 
        ForeignKey("subscription_tiers.tier_id", ondelete="SET NULL"), 
        nullable=True
    )
    
    plan_name = Column(String, nullable=False)  # Keep for backward compatibility
    status = Column(
        Enum("trialing", "active", "past_due", "cancelled", name="subscription_statuses"),
        nullable=False,
        server_default="trialing",
    )

    provider = Column(String, nullable=False, default="paystack")
    # REMOVED: provider_customer_id (now in users table)

    current_period_start = Column(TIMESTAMP, nullable=False)
    current_period_end = Column(TIMESTAMP, nullable=False)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_subscriptions_user_status", "user_id", "status"),
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
    payment_metadata  = Column(JSON, default={})

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_payments_user_subscription_status", "user_id", "subscription_id", "status"),
        Index("ix_payments_gym_status", "gym_id", "status"),
    )
    
    # Relationships
    user = relationship("User")
    subscription = relationship("Subscription", back_populates="payments")
    gym = relationship("Gym")
    payout = relationship("Payout", uselist=False, back_populates="payment")


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