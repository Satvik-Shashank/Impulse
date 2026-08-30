"""SQLAlchemy models for persistent dispute database & decision audit logs."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class DisputeModel(Base):
    __tablename__ = "disputes"

    id = Column(String, primary_key=True, index=True)
    reason_code = Column(String, index=True, nullable=False)
    reason_code_label = Column(String, nullable=True)
    card_network = Column(String, nullable=False)
    dispute_amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    transaction_date = Column(String, nullable=False)
    days_to_dispute = Column(Integer, nullable=False)
    product_category = Column(String, nullable=False)
    shipping_method = Column(String, nullable=False)
    
    # Evidence booleans
    delivery_confirmed = Column(Boolean, default=False)
    has_delivery_proof = Column(Boolean, default=False)
    ip_geolocation_match = Column(Boolean, default=False)
    avs_cvv_match = Column(String, default="neither")
    has_3ds_authentication = Column(Boolean, default=False)
    has_customer_correspondence = Column(Boolean, default=False)

    # Customer signals
    customer_account_age_days = Column(Integer, default=0)
    customer_prior_disputes = Column(Integer, default=0)
    customer_prior_orders = Column(Integer, default=0)

    # Pipeline outcome & state
    status = Column(String, default="PENDING")  # PENDING, AUTO_SUBMITTED, HUMAN_REVIEW, MERCHANT_APPROVED, WON, LOST
    predicted_reason_code = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)
    evidence_strength = Column(Float, nullable=True)
    action_decision = Column(String, nullable=True)
    generated_response_text = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    attachments = relationship("EvidenceAttachmentModel", back_populates="dispute", cascade="all, delete-orphan")
    audit_logs = relationship("DecisionAuditLogModel", back_populates="dispute", cascade="all, delete-orphan")


class EvidenceAttachmentModel(Base):
    __tablename__ = "evidence_attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dispute_id = Column(String, ForeignKey("disputes.id"), nullable=False)
    evidence_type = Column(String, nullable=False)  # DELIVERY_PROOF, 3DS_LOG, AVS_CVV, CUSTOMER_COMMUNICATION, POLICY_TERMS
    file_name = Column(String, nullable=False)
    file_size_bytes = Column(Integer, default=0)
    summary = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    dispute = relationship("DisputeModel", back_populates="attachments")


class DecisionAuditLogModel(Base):
    __tablename__ = "decision_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dispute_id = Column(String, ForeignKey("disputes.id"), nullable=False)
    predicted_reason_code = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=False)
    evidence_strength = Column(Float, nullable=False)
    action_taken = Column(String, nullable=False)
    cost_fp = Column(Float, default=1000.0)
    cost_fn = Column(Float, default=350.0)
    savings_tp = Column(Float, default=2250.0)
    estimated_net_value = Column(Float, nullable=False)
    evaluated_at = Column(DateTime, default=datetime.utcnow)

    dispute = relationship("DisputeModel", back_populates="audit_logs")
