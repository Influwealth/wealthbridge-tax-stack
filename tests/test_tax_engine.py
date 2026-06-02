from decimal import Decimal
from tax_capsule.tax_engine import calculate_tax
from tax_capsule.utils.schemas import TaxCalculationRequest


def test_basic_corporation():
    req = TaxCalculationRequest(income=Decimal("100000"), expenses=Decimal("20000"))
    result = calculate_tax(req)
    assert result["taxable_income"] == Decimal("80000")
    assert result["tax_due"] == Decimal("16800.00")  # 80000 * 0.21


def test_expenses_exceed_income():
    req = TaxCalculationRequest(income=Decimal("10000"), expenses=Decimal("50000"))
    result = calculate_tax(req)
    assert result["taxable_income"] == Decimal("0")
    assert result["tax_due"] == Decimal("0.00")


def test_partnership_zero_tax():
    req = TaxCalculationRequest(
        income=Decimal("100000"), expenses=Decimal("0"), entity_type="partnership"
    )
    result = calculate_tax(req)
    assert result["tax_due"] == Decimal("0.00")
    assert result["form_hint"] == "1065"


def test_corporation_form_hint():
    req = TaxCalculationRequest(income=Decimal("100000"), entity_type="corporation")
    result = calculate_tax(req)
    assert result["form_hint"] == "1120"


def test_employer_form_hint():
    req = TaxCalculationRequest(income=Decimal("100000"), entity_type="employer")
    result = calculate_tax(req)
    assert result["form_hint"] == "941"


def test_default_form_hint():
    req = TaxCalculationRequest(income=Decimal("100000"))
    result = calculate_tax(req)
    assert result["form_hint"] == "1120"
