import enum
from sqlalchemy import Column, Integer, Numeric, String, Boolean, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import relationship
from app.database import Base


class RoleEnum(str, enum.Enum):
    admin = "admin"
    accountant = "accountant"
    business_owner = "business_owner"
    agent = "agent"
    auditor = "auditor"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())

    tax_records = relationship("TaxRecord", back_populates="creator", foreign_keys="TaxRecord.created_by")
    # Explicit foreign_keys to resolve the two-FK ambiguity on UserRole
    user_roles = relationship(
        "UserRole",
        back_populates="user",
        foreign_keys="UserRole.user_id",
        cascade="all, delete-orphan",
    )

    @property
    def roles(self) -> list[str]:
        return [ur.role for ur in self.user_roles]

    def has_role(self, role: str) -> bool:
        return role in self.roles


class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(Enum(RoleEnum), nullable=False)
    granted_at = Column(DateTime(timezone=True), default=func.now())
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    user = relationship("User", foreign_keys=[user_id], back_populates="user_roles")


class TaxRecord(Base):
    __tablename__ = "tax_records"

    id = Column(Integer, primary_key=True, index=True)
    entity_name = Column(String(255), index=True, nullable=False)
    tax_year = Column(Integer, index=True, nullable=False)
    income = Column(Numeric(18, 2), nullable=False)
    expenses = Column(Numeric(18, 2), nullable=False, default=0)
    tax_due = Column(Numeric(18, 2), nullable=True)
    entity_type = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    creator = relationship("User", foreign_keys=[created_by], back_populates="tax_records")
