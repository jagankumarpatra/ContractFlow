from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
import json
from app.db.base import Base

class ContractStatus(str, enum.Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    SIGNED = "signed"
    EXPIRED = "expired"
    TERMINATED = "terminated"

class ContractType(str, enum.Enum):
    NDA = "nda"
    SERVICE_AGREEMENT = "service_agreement"
    EMPLOYMENT = "employment"
    VENDOR = "vendor"
    PARTNERSHIP = "partnership"
    OTHER = "other"

class Contract(Base):
    __tablename__ = "contracts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    title = Column(String(500), nullable=False)
    contract_type = Column(SAEnum(ContractType), default=ContractType.OTHER)
    status = Column(SAEnum(ContractStatus), default=ContractStatus.DRAFT, index=True)
    description = Column(Text, nullable=True)

    party_a = Column(String(255), nullable=True)
    party_b = Column(String(255), nullable=True)

    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)

    file_url = Column(String(1000), nullable=True)
    file_name = Column(String(500), nullable=True)
    contract_text = Column(Text, nullable=True)

    # Store as TEXT for SQLite compat; PostgreSQL will use native JSON
    ai_analysis_raw = Column("ai_analysis", Text, nullable=True)
    ai_analyzed_at = Column(DateTime(timezone=True), nullable=True)

    is_expiry_notified = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    company = relationship("Company", back_populates="contracts")
    created_by = relationship("User", back_populates="contracts")

    @property
    def ai_analysis(self):
        if self.ai_analysis_raw:
            try:
                return json.loads(self.ai_analysis_raw)
            except Exception:
                return self.ai_analysis_raw
        return None

    @ai_analysis.setter
    def ai_analysis(self, value):
        self.ai_analysis_raw = json.dumps(value) if value is not None else None
