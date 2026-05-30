from decimal import Decimal
from rd_plugin.rd_core import run_rd_analysis


def test_rd_basic():
    data = {
        "project_name": "AI Tax Engine",
        "qualified_expenses": "50000",
        "total_wages": "120000",
        "supply_costs": "10000",
    }
    result = run_rd_analysis(data)
    assert result["status"] == "ANALYZED"
    assert Decimal(result["estimated_credit"]) > Decimal("0")
    assert result["method"] == "Alternative Simplified Credit (IRC §41)"
    assert result["project"] == "AI Tax Engine"


def test_rd_zero_expenses():
    result = run_rd_analysis({"project_name": "Empty", "qualified_expenses": "0"})
    assert result["estimated_credit"] == "0.00"
    assert result["status"] == "ANALYZED"


def test_rd_contract_research_discount():
    data = {
        "project_name": "Contract Project",
        "qualified_expenses": "0",
        "contract_research": "100000",
    }
    result = run_rd_analysis(data)
    # 65% of 100000 = 65000; 65000 * 0.14 = 9100
    assert result["contract_research_65pct"] == "65000.00"
    assert result["estimated_credit"] == "9100.00"
