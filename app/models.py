from sqlalchemy import Column, Integer, Numeric, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())

    tax_records = relationship("TaxRecord", back_populates="creator")


class TaxRecord(Base):
    __tablename__ = "tax_records"

    id = Column(Integer, primary_key=True, index=True)
    entity_name = Column(String(255), index=True, nullable=False)
    tax_year = Column(Integer, index=True, nullable=False)
    income = Column(Numeric(18, 2), nullable=False)
    expenses = Column(Numeric(18, 2), nullable=False, default=0)
    tax_due = Column(Numeric(18, 2), nullable=True)
    entity_type = Column(String(50), nullable=True)  # partnership, corporation, employer
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    creator = relationship("User", back_populates="tax_records")
