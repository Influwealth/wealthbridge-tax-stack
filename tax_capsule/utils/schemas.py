from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal, List
from datetime import datetime
from decimal import Decimal


# --- RBAC ---
class RoleAssign(BaseModel):
    username: str
    role: Literal["admin", "accountant", "business_owner", "agent", "auditor"]


class RoleRevoke(BaseModel):
    username: str
    role: Literal["admin", "accountant", "business_owner", "agent", "auditor"]


class UserRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    granted_at: datetime


class UserWithRolesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    is_active: bool
    roles: List[str]


# --- Auth ---
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=150)
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Tax Calculation ---
class TaxCalculationRequest(BaseModel):
    income: Decimal = Field(..., gt=0, description="Total gross income")
    expenses: Optional[Decimal] = Field(Decimal("0"), ge=0)
    entity_type: Optional[Literal[
        "partnership", "corporation", "employer",
        "sole_proprietor", "contractor", "employee"
    ]] = None


class TaxResponse(BaseModel):
    taxable_income: Decimal
    tax_due: Decimal
    currency: str = "USD"
    form_hint: Optional[str] = None


# --- Tax Records CRUD ---
class TaxRecordCreate(BaseModel):
    entity_name: str = Field(..., min_length=1, max_length=255)
    tax_year: int = Field(..., ge=2000, le=2100)
    income: Decimal = Field(..., gt=0)
    expenses: Optional[Decimal] = Field(Decimal("0"), ge=0)
    entity_type: Optional[Literal[
        "partnership", "corporation", "employer",
        "sole_proprietor", "contractor", "employee"
    ]] = None


class TaxRecordUpdate(BaseModel):
    entity_name: Optional[str] = Field(None, min_length=1, max_length=255)
    income: Optional[Decimal] = Field(None, gt=0)
    expenses: Optional[Decimal] = Field(None, ge=0)
    entity_type: Optional[Literal[
        "partnership", "corporation", "employer",
        "sole_proprietor", "contractor", "employee"
    ]] = None


class TaxRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    entity_name: str
    tax_year: int
    income: Decimal
    expenses: Decimal
    tax_due: Optional[Decimal]
    entity_type: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


# --- R&D ---
class RDAnalysisRequest(BaseModel):
    project_name: str
    qualified_expenses: Decimal
    total_wages: Optional[Decimal] = None
    supply_costs: Optional[Decimal] = None
    contract_research: Optional[Decimal] = None
