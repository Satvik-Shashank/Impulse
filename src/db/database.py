"""Database manager for SQLite storage of disputes, attachments, and audit trails."""

import os
import json
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.db.models import Base, DisputeModel, EvidenceAttachmentModel, DecisionAuditLogModel
from src.pipeline.run import ChargebackResponder

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "chargebacks.db")

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all SQLite database tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency helper for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_dispute_and_process(dispute_dict: dict, db: Session, model_path: str = "models/classifier.pkl") -> dict:
    """Save a dispute to SQLite database, execute AI pipeline, record audit log, and return full output."""
    init_db()

    dispute_id = dispute_dict.get("dispute_id")
    if not dispute_id:
        dispute_id = f"DSP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        dispute_dict["dispute_id"] = dispute_id

    # Run AI pipeline
    responder = ChargebackResponder(model_path=model_path)
    result = responder.process(dispute_dict)

    clf_out = result["classification"]
    ev_out = result["evidence"]
    resp_out = result["response"]

    status = resp_out["action"]  # AUTO_SUBMITTED or HUMAN_REVIEW

    # Check if record already exists
    existing = db.query(DisputeModel).filter(DisputeModel.id == dispute_id).first()
    if existing:
        db.delete(existing)
        db.commit()

    # Create Dispute DB record
    db_dispute = DisputeModel(
        id=dispute_id,
        reason_code=dispute_dict.get("reason_code", "10.4"),
        reason_code_label=dispute_dict.get("reason_code_label", ""),
        card_network=dispute_dict.get("card_network", "Visa"),
        dispute_amount=float(dispute_dict.get("dispute_amount", 0.0)),
        currency=dispute_dict.get("currency", "INR"),
        transaction_date=str(dispute_dict.get("transaction_date", datetime.now().strftime("%Y-%m-%d"))),
        days_to_dispute=int(dispute_dict.get("days_to_dispute", 10)),
        product_category=str(dispute_dict.get("product_category", "electronics")),
        shipping_method=str(dispute_dict.get("shipping_method", "standard")),
        delivery_confirmed=bool(dispute_dict.get("delivery_confirmed", False)),
        has_delivery_proof=bool(dispute_dict.get("has_delivery_proof", False)),
        ip_geolocation_match=bool(dispute_dict.get("ip_geolocation_match", False)),
        avs_cvv_match=str(dispute_dict.get("avs_cvv_match", "neither")),
        has_3ds_authentication=bool(dispute_dict.get("has_3ds_authentication", False)),
        has_customer_correspondence=bool(dispute_dict.get("has_customer_correspondence", False)),
        customer_account_age_days=int(dispute_dict.get("customer_account_age_days", 30)),
        customer_prior_disputes=int(dispute_dict.get("customer_prior_disputes", 0)),
        customer_prior_orders=int(dispute_dict.get("customer_prior_orders", 1)),
        status=status,
        predicted_reason_code=clf_out["predicted_reason_code"],
        confidence_score=clf_out["confidence"],
        evidence_strength=ev_out["evidence_strength"],
        action_decision=status,
        generated_response_text=resp_out["response_text"],
    )

    db.add(db_dispute)
    db.commit()

    # Net cost calculation
    cost_fp = 1000.0
    cost_fn = 350.0
    savings_tp = 2250.0
    net_val = (savings_tp if status == "AUTO_SUBMITTED" else -cost_fn)

    # Record Audit Log
    audit_log = DecisionAuditLogModel(
        dispute_id=dispute_id,
        predicted_reason_code=clf_out["predicted_reason_code"],
        confidence_score=clf_out["confidence"],
        evidence_strength=ev_out["evidence_strength"],
        action_taken=status,
        cost_fp=cost_fp,
        cost_fn=cost_fn,
        savings_tp=savings_tp,
        estimated_net_value=net_val,
    )
    db.add(audit_log)
    db.commit()

    return result


def seed_database_if_empty(db: Session, n: int = 50, model_path: str = "models/classifier.pkl"):
    """Seed the SQLite database with n realistic synthetic dispute records if empty."""
    init_db()
    count = db.query(DisputeModel).count()
    if count >= n:
        return count

    from src.data.generate_disputes import generate_dispute
    for i in range(n):
        d = generate_dispute(i + 100)
        save_dispute_and_process(d, db, model_path=model_path)

    return db.query(DisputeModel).count()
