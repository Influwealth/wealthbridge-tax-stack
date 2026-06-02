"""
Shared base class and validation layer for all IRS form generators.
All form generators must subclass FormBase or call validate_record().
"""
from decimal import Decimal
from dataclasses import dataclass
from typing import Optional


VALID_ENTITY_TYPES = {
    "partnership", "corporation", "employer",
    "sole_proprietor", "contractor", "employee",
}


class FormValidationError(ValueError):
    pass


def validate_record(record, expected_entity_type: Optional[str] = None) -> None:
    """Raise FormValidationError if the record is not suitable for form generation."""
    if not record.entity_name or not str(record.entity_name).strip():
        raise FormValidationError("entity_name is required")
    if not record.tax_year or int(record.tax_year) < 2000:
        raise FormValidationError("tax_year must be >= 2000")
    try:
        income = Decimal(str(record.income))
        if income < 0:
            raise FormValidationError("income must be non-negative")
    except Exception:
        raise FormValidationError("income must be a valid number")
    if expected_entity_type and record.entity_type != expected_entity_type:
        raise FormValidationError(
            f"entity_type must be '{expected_entity_type}', got '{record.entity_type}'"
        )


def to_dec(value, default="0") -> Decimal:
    """Safely convert a model field to Decimal."""
    try:
        return Decimal(str(value)) if value is not None else Decimal(default)
    except Exception:
        return Decimal(default)


@dataclass
class FormRecord:
    """Lightweight data-transfer object — avoids SQLAlchemy model coupling in tests."""
    entity_name: str
    tax_year: int
    income: Decimal
    expenses: Decimal = Decimal("0")
    entity_type: Optional[str] = None
    wages: Optional[Decimal] = None       # W-2 / 941 specific
    compensation: Optional[Decimal] = None  # 1099-NEC specific
