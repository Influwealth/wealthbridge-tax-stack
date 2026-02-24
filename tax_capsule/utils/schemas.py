from pydantic import BaseModel, Field
from typing import Optional

class TaxCalculationRequest(BaseModel):
    income: float = Field(..., gt=0, description="Total gross income")
    expenses: Optional[float] = Field(0, ge=0)

class TaxResponse(BaseModel):
    taxable_income: float
    tax_due: float
    currency: str = "USD"
