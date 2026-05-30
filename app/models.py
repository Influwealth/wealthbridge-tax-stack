import enum
from sqlalchemy import Column, Integer, Numeric, String, Boolean, DateTime, ForeignKey, Enum, Text, func
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


class TaxDocument(Base):
    __tablename__ = "tax_documents"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("tax_records.id", ondelete="CASCADE"), nullable=False, index=True)
    doc_type = Column(String(50), nullable=False, index=True)
    format = Column(String(10), nullable=False)
    vault_key = Column(String(255), nullable=False)
    size_bytes = Column(Integer, nullable=True)
    checksum_sha256 = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    record = relationship("TaxRecord", back_populates="documents")


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
    documents = relationship("TaxDocument", back_populates="record", cascade="all, delete-orphan")
    rd_projects = relationship("RDProject", back_populates="record", cascade="all, delete-orphan")


class RDProject(Base):
    __tablename__ = "rd_projects"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("tax_records.id", ondelete="CASCADE"), nullable=False, index=True)
    project_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    activity_type = Column(String(50), nullable=True)
    is_qualified = Column(Boolean, default=False, nullable=False)
    principal_researcher = Column(String(200), nullable=True)
    start_date = Column(String(20), nullable=True)   # ISO date string
    end_date = Column(String(20), nullable=True)
    is_ongoing = Column(Boolean, default=False)
    total_qre = Column(Numeric(18, 2), default=0, nullable=False)
    estimated_credit = Column(Numeric(18, 2), default=0, nullable=False)
    validation_score = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())

    record = relationship("TaxRecord", back_populates="rd_projects")
    expenses = relationship("RDExpense", back_populates="project", cascade="all, delete-orphan")
    rd_documents = relationship("RDDocument", back_populates="project", cascade="all, delete-orphan")


class RDExpense(Base):
    __tablename__ = "rd_expenses"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("rd_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(50), nullable=False)
    description = Column(String(500), nullable=True)
    amount = Column(Numeric(18, 2), nullable=False)
    qualification_rate = Column(Numeric(5, 4), nullable=False, default=1)
    qualified_amount = Column(Numeric(18, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())

    project = relationship("RDProject", back_populates="expenses")


class RDDocument(Base):
    __tablename__ = "rd_documents"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("rd_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    doc_name = Column(String(200), nullable=False)
    doc_type = Column(String(50), nullable=True)
    is_valid = Column(Boolean, default=False)
    validation_score = Column(Integer, default=0)
    issues = Column(Text, nullable=True)  # JSON-encoded list
    uploaded_at = Column(DateTime(timezone=True), default=func.now())

    project = relationship("RDProject", back_populates="rd_documents")
