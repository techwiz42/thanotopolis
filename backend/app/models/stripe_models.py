"""
Stripe-related database models
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from app.models.models import Base


class StripeCustomer(Base):
    __tablename__ = "stripe_customers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True)
    stripe_customer_id = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="stripe_customer")
    subscriptions = relationship("StripeSubscription", back_populates="customer", cascade="all, delete-orphan")
    invoices = relationship("StripeInvoice", back_populates="customer", cascade="all, delete-orphan")


class StripeSubscription(Base):
    __tablename__ = "stripe_subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("stripe_customers.id"), nullable=False)
    stripe_subscription_id = Column(String, nullable=False, unique=True)
    stripe_price_id = Column(String, nullable=False)
    status = Column(String, nullable=False)  # active, past_due, canceled, etc.
    current_period_start = Column(DateTime(timezone=True), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    cancel_at_period_end = Column(Boolean, default=False)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String, default='usd')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    customer = relationship("StripeCustomer", back_populates="subscriptions")


class StripeInvoice(Base):
    __tablename__ = "stripe_invoices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("stripe_customers.id"), nullable=False)
    stripe_invoice_id = Column(String, nullable=False, unique=True)
    status = Column(String, nullable=False)  # draft, open, paid, void, uncollectible
    amount_due_cents = Column(Integer, nullable=False)
    amount_paid_cents = Column(Integer, nullable=True)
    currency = Column(String, default='usd')
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    voice_words_count = Column(Integer, nullable=True)
    voice_usage_cents = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    due_date = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    customer = relationship("StripeCustomer", back_populates="invoices")