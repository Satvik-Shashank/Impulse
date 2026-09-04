"""Thread-safe dispute storage wrapper over the SQLite database.

Provides a simplified interface for the API layer to persist dispute
inputs, pipeline outcomes, and retrieve aggregate analytics for the
dashboard without leaking ORM internals into the route handlers.
"""

import os
import json
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, func, desc
from sqlalchemy.orm import sessionmaker, Session

from src.db.models import Base, DisputeModel, DecisionAuditLogModel

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_DIR = os.path.join(_PROJECT_ROOT, "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "chargebacks.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
PERSISTENCE_MODE = "managed" if os.getenv("DATABASE_URL") else "local_development"


def _number(value, default=0.0):
    """Convert persisted numeric input without allowing blank strings to escape."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    return float(value)


def _integer(value, default=0):
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    return int(value)

engine_kwargs = {"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _init_tables():
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    _init_tables()
    return SessionLocal()


class DisputeStore:
    """High-level facade for dispute persistence."""

    def save_result(self, dispute_dict: dict, pipeline_result: dict) -> str:
        """Persist the original dispute and the pipeline output. Returns dispute_id."""
        db = get_session()
        try:
            dispute_id = dispute_dict.get("dispute_id", f"DSP-{datetime.now().strftime('%Y%m%d%H%M%S')}")
            clf = pipeline_result.get("classification", {})
            ev = pipeline_result.get("evidence", {})
            resp = pipeline_result.get("response", {})

            # Remove existing record if re-processing
            existing = db.query(DisputeModel).filter(DisputeModel.id == dispute_id).first()
            if existing:
                db.delete(existing)
                db.commit()

            action = resp.get("action", "HUMAN_REVIEW")
            record = DisputeModel(
                id=dispute_id,
                reason_code=dispute_dict.get("reason_code", clf.get("predicted_reason_code", "unknown")),
                reason_code_label=dispute_dict.get("reason_code_label", ""),
                card_network=dispute_dict.get("card_network", "Visa"),
                dispute_amount=_number(dispute_dict.get("dispute_amount")),
                currency=dispute_dict.get("currency", "INR"),
                transaction_date=str(dispute_dict.get("transaction_date", "")),
                days_to_dispute=_integer(dispute_dict.get("days_to_dispute")),
                product_category=str(dispute_dict.get("product_category", "")),
                shipping_method=str(dispute_dict.get("shipping_method", "")),
                delivery_confirmed=bool(dispute_dict.get("delivery_confirmed", False)),
                has_delivery_proof=bool(dispute_dict.get("has_delivery_proof", False)),
                ip_geolocation_match=bool(dispute_dict.get("ip_geolocation_match", False)),
                avs_cvv_match=str(dispute_dict.get("avs_cvv_match", "neither")),
                has_3ds_authentication=bool(dispute_dict.get("has_3ds_authentication", False)),
                has_customer_correspondence=bool(dispute_dict.get("has_customer_correspondence", False)),
                customer_account_age_days=_integer(dispute_dict.get("customer_account_age_days")),
                customer_prior_disputes=_integer(dispute_dict.get("customer_prior_disputes")),
                customer_prior_orders=_integer(dispute_dict.get("customer_prior_orders")),
                status=action,
                predicted_reason_code=clf.get("predicted_reason_code", ""),
                confidence_score=clf.get("confidence", 0.0),
                evidence_strength=ev.get("evidence_strength", 0.0),
                action_decision=action,
                generated_response_text=resp.get("response_text", ""),
            )
            db.add(record)

            # Audit log
            audit = DecisionAuditLogModel(
                dispute_id=dispute_id,
                predicted_reason_code=clf.get("predicted_reason_code", ""),
                confidence_score=clf.get("confidence", 0.0),
                evidence_strength=ev.get("evidence_strength", 0.0),
                action_taken=action,
                cost_fp=1000.0,
                cost_fn=350.0,
                savings_tp=2250.0,
                estimated_net_value=pipeline_result.get("expected_value_inr", 0.0),
            )
            db.add(audit)
            db.commit()
            return dispute_id
        finally:
            db.close()

    def get_dispute(self, dispute_id: str) -> Optional[dict]:
        """Retrieve a single dispute record by ID."""
        db = get_session()
        try:
            record = db.query(DisputeModel).filter(DisputeModel.id == dispute_id).first()
            if not record:
                return None
            return self._to_dict(record)
        finally:
            db.close()

    def list_disputes(self, page: int = 1, per_page: int = 20,
                      action: str = None, reason_code: str = None) -> dict:
        """Paginated dispute listing with optional filters."""
        db = get_session()
        try:
            query = db.query(DisputeModel).order_by(desc(DisputeModel.created_at))
            if action:
                query = query.filter(DisputeModel.action_decision == action)
            if reason_code:
                query = query.filter(DisputeModel.predicted_reason_code == reason_code)

            total = query.count()
            items = query.offset((page - 1) * per_page).limit(per_page).all()
            return {
                "total": total,
                "page": page,
                "per_page": per_page,
                "items": [self._to_dict(r) for r in items],
            }
        finally:
            db.close()

    def get_dashboard_summary(self) -> dict:
        """Aggregate metrics for the dashboard overview."""
        db = get_session()
        try:
            total = db.query(DisputeModel).count()
            if total == 0:
                return {
                    "total_disputes": 0,
                    "auto_submitted": 0,
                    "human_review": 0,
                    "auto_rate_pct": 0.0,
                    "avg_confidence": 0.0,
                    "avg_evidence_strength": 0.0,
                    "total_estimated_value_inr": 0.0,
                    "reason_code_distribution": {},
                }

            auto = db.query(DisputeModel).filter(
                DisputeModel.action_decision == "AUTO_SUBMIT").count()
            human = total - auto

            avg_conf = db.query(func.avg(DisputeModel.confidence_score)).scalar() or 0.0
            avg_ev = db.query(func.avg(DisputeModel.evidence_strength)).scalar() or 0.0

            total_value = db.query(
                func.sum(DecisionAuditLogModel.estimated_net_value)
            ).scalar() or 0.0

            rc_dist_rows = db.query(
                DisputeModel.predicted_reason_code,
                func.count(DisputeModel.id)
            ).group_by(DisputeModel.predicted_reason_code).all()

            return {
                "total_disputes": total,
                "auto_submitted": auto,
                "human_review": human,
                "auto_rate_pct": round(auto / total * 100, 1) if total else 0.0,
                "avg_confidence": round(float(avg_conf), 4),
                "avg_evidence_strength": round(float(avg_ev), 4),
                "total_estimated_value_inr": round(float(total_value), 2),
                "reason_code_distribution": {
                    row[0]: row[1] for row in rc_dist_rows if row[0]
                },
            }
        finally:
            db.close()

    @staticmethod
    def _to_dict(record: DisputeModel) -> dict:
        return {
            "dispute_id": record.id,
            "reason_code": record.reason_code,
            "reason_code_label": record.reason_code_label,
            "card_network": record.card_network,
            "dispute_amount": record.dispute_amount,
            "currency": record.currency,
            "transaction_date": record.transaction_date,
            "days_to_dispute": record.days_to_dispute,
            "product_category": record.product_category,
            "shipping_method": record.shipping_method,
            "status": record.status,
            "predicted_reason_code": record.predicted_reason_code,
            "confidence_score": record.confidence_score,
            "evidence_strength": record.evidence_strength,
            "action_decision": record.action_decision,
            "generated_response_text": record.generated_response_text,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }
