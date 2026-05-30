from decimal import Decimal
from irs_forms.form_1065 import generate_1065
from irs_forms.form_1120 import generate_1120
from irs_forms.form_941 import generate_941


class FakeRecord:
    def __init__(self, name, year, income, expenses, entity_type=None):
        self.entity_name = name
        self.tax_year = year
        self.income = income
        self.expenses = expenses
        self.entity_type = entity_type


def test_form_1065():
    rec = FakeRecord("Alpha Partners", 2024, Decimal("500000"), Decimal("100000"), "partnership")
    result = generate_1065(rec)
    assert result["form"] == "1065"
    assert result["entity_level_tax"] == "0.00"
    assert result["line_22_ordinary_business_income"] == "400000"


def test_form_1065_zero_profit():
    rec = FakeRecord("Zero Partners", 2024, Decimal("50000"), Decimal("200000"), "partnership")
    result = generate_1065(rec)
    assert result["line_22_ordinary_business_income"] == "0"


def test_form_1120():
    rec = FakeRecord("Beta Corp", 2024, Decimal("1000000"), Decimal("300000"), "corporation")
    result = generate_1120(rec)
    assert result["form"] == "1120"
    assert result["line_28_taxable_income"] == "700000"
    assert result["line_31_total_tax"] == "147000.00"  # 700000 * 0.21


def test_form_1120_no_expenses():
    rec = FakeRecord("Corp Zero", 2024, Decimal("100000"), Decimal("0"), "corporation")
    result = generate_1120(rec)
    assert Decimal(result["line_31_total_tax"]) == Decimal("21000.00")


def test_form_941_quarter():
    rec = FakeRecord("Gamma LLC", 2024, Decimal("100000"), Decimal("0"), "employer")
    result = generate_941(rec, quarter=2)
    assert result["form"] == "941"
    assert result["quarter"] == 2
    assert Decimal(result["line_6_total_taxes"]) > Decimal("0")


def test_form_941_quarter_clamped():
    rec = FakeRecord("Delta LLC", 2024, Decimal("50000"), Decimal("0"), "employer")
    result = generate_941(rec, quarter=5)
    assert result["quarter"] == 4  # clamped to max 4
