"""Wave 5: QRE Agent — classifier, scorer, validator, engine, and API tests."""
import pytest
from decimal import Decimal
from qre_agent.classifier import classify_activity, is_qualified_activity, ActivityType
from qre_agent.scorer import (
    score_expense, score_all_expenses, ExpenseCategory, ExpenseRecord
)
from qre_agent.validator import validate_project_documentation, PASSING_SCORE
from qre_agent.engine import calculate_credit, analyze_project


# ─── Classifier ───────────────────────────────────────────────────────────────

def test_classify_software_development():
    result = classify_activity("Building a machine learning algorithm for fraud detection")
    assert result == ActivityType.software_development


def test_classify_new_product():
    result = classify_activity("We are creating a novel patent-pending product for biotech")
    assert result == ActivityType.new_product or result in (
        ActivityType.basic_research, ActivityType.new_product
    )
    # Should not be non_qualified
    assert result != ActivityType.non_qualified


def test_classify_process_improvement():
    result = classify_activity("Optimizing manufacturing process and production workflow yield")
    assert result == ActivityType.process_improvement


def test_classify_non_qualified_marketing():
    result = classify_activity("Developing marketing and advertising strategy for sales campaigns")
    assert result == ActivityType.non_qualified


def test_classify_non_qualified_style():
    result = classify_activity("Improving aesthetic style and taste of product packaging")
    assert result == ActivityType.non_qualified


def test_is_qualified_activity_true():
    assert is_qualified_activity(ActivityType.software_development) is True
    assert is_qualified_activity(ActivityType.basic_research) is True
    assert is_qualified_activity(ActivityType.new_product) is True


def test_is_qualified_activity_false():
    assert is_qualified_activity(ActivityType.non_qualified) is False


# ─── Scorer ───────────────────────────────────────────────────────────────────

def test_score_wages_100pct():
    s = score_expense(ExpenseCategory.wages, Decimal("100000"))
    assert s.qualification_rate == Decimal("1.00")
    assert s.qualified_amount == Decimal("100000")


def test_score_contract_research_65pct():
    s = score_expense(ExpenseCategory.contract_research, Decimal("100000"))
    assert s.qualification_rate == Decimal("0.65")
    assert s.qualified_amount == Decimal("65000.00")


def test_score_non_qualified_zero():
    s = score_expense(ExpenseCategory.non_qualified, Decimal("50000"))
    assert s.qualified_amount == Decimal("0.00")


def test_score_all_expenses_totals():
    expenses = [
        ExpenseRecord(ExpenseCategory.wages, Decimal("80000")),
        ExpenseRecord(ExpenseCategory.supplies, Decimal("20000")),
        ExpenseRecord(ExpenseCategory.contract_research, Decimal("30000")),
    ]
    result = score_all_expenses(expenses)
    # 80000 + 20000 + 30000*0.65 = 119500
    assert result["total_qre"] == "119500.00"
    assert result["total_amount"] == "130000.00"
    assert "wages" in result["by_category"]
    assert "contract_research" in result["by_category"]


def test_score_all_expenses_by_category_accuracy():
    expenses = [
        ExpenseRecord(ExpenseCategory.contract_research, Decimal("10000")),
    ]
    result = score_all_expenses(expenses)
    cat = result["by_category"]["contract_research"]
    assert cat["qualified_amount"] == "6500.00"
    assert cat["qualification_rate"] == "0.65"


# ─── Validator ────────────────────────────────────────────────────────────────

def test_validate_complete_project():
    data = {
        "project_name": "ML Fraud Detection System",
        "description": "A" * 210,  # > 200 chars
        "activity_type": "software_development",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "principal_researcher": "Dr. Jane Smith",
        "has_expenses": True,
        "expense_count": 3,
    }
    result = validate_project_documentation(data)
    assert result.is_valid is True
    assert result.score >= PASSING_SCORE


def test_validate_minimal_project():
    data = {"project_name": "X", "description": "short"}
    result = validate_project_documentation(data)
    assert result.is_valid is False
    assert len(result.issues) > 0


def test_validate_non_qualified_activity_flagged():
    data = {
        "project_name": "Marketing Campaign",
        "description": "B" * 200,
        "activity_type": "non_qualified",
        "has_expenses": True,
    }
    result = validate_project_documentation(data)
    assert any("non-qualified" in i.lower() or "not qualified" in i.lower() or "4-part" in i for i in result.issues)


def test_validate_no_expenses_issue():
    data = {
        "project_name": "Test Project",
        "description": "C" * 200,
        "activity_type": "software_development",
        "has_expenses": False,
        "expense_count": 0,
    }
    result = validate_project_documentation(data)
    assert any("expense" in i.lower() for i in result.issues)


# ─── Engine ───────────────────────────────────────────────────────────────────

def test_calculate_credit_basic():
    expenses = [
        {"category": "wages", "amount": "100000"},
        {"category": "supplies", "amount": "20000"},
    ]
    result = calculate_credit(expenses)
    # total_qre = 120000, credit = 14% × 120000 = 16800
    assert result["total_qre"] == "120000.00"
    assert result["estimated_credit"] == "16800.00"
    assert result["credit_rate"] == "0.14"
    assert result["status"] == "CALCULATED"


def test_calculate_credit_with_contract_research():
    expenses = [
        {"category": "wages", "amount": "50000"},
        {"category": "contract_research", "amount": "100000"},
    ]
    result = calculate_credit(expenses)
    # total_qre = 50000 + 65000 = 115000
    assert result["total_qre"] == "115000.00"
    assert result["estimated_credit"] == str(Decimal("115000") * Decimal("0.14"))


def test_calculate_credit_startup_rate():
    expenses = [{"category": "wages", "amount": "100000"}]
    result = calculate_credit(expenses, is_startup=True)
    # startup rate = 6%
    assert result["credit_rate"] == "0.06"
    assert result["estimated_credit"] == "6000.00"


def test_calculate_credit_with_prior_qre():
    expenses = [{"category": "wages", "amount": "200000"}]
    prior_avg = Decimal("100000")
    result = calculate_credit(expenses, prior_qre_avg=prior_avg)
    # incremental = 200000 - 50% × 100000 = 150000; credit = 14% × 150000 = 21000
    assert result["estimated_credit"] == "21000.00"


def test_analyze_project_qualified():
    project_data = {
        "project_name": "ML Encryption Platform",
        "description": "Building a distributed machine learning platform with advanced encryption algorithms",
        "start_date": "2024-01-01",
        "principal_researcher": "Dr. Smith",
    }
    expenses = [{"category": "wages", "amount": "50000"}]
    result = analyze_project(project_data, expenses)

    assert result["is_qualified"] is True
    assert result["credit_calculation"]["status"] == "CALCULATED"
    assert Decimal(result["credit_calculation"]["estimated_credit"]) > 0


def test_analyze_project_non_qualified():
    project_data = {
        "project_name": "Ad Campaign",
        "description": "Marketing and advertising strategy for product launch",
    }
    expenses = [{"category": "wages", "amount": "10000"}]
    result = analyze_project(project_data, expenses)

    assert result["is_qualified"] is False
    assert result["credit_calculation"]["status"] == "NOT_QUALIFIED"


def test_analyze_project_no_expenses():
    project_data = {
        "project_name": "Software Dev Project",
        "description": "Developing new software algorithm for optimization",
    }
    result = analyze_project(project_data, [])
    assert result["credit_calculation"]["status"] == "NO_EXPENSES"


# ─── rd_plugin backward compatibility ────────────────────────────────────────

def test_rd_plugin_wrapper():
    from rd_plugin.rd_core import run_rd_analysis
    result = run_rd_analysis({
        "project_name": "Test Project",
        "qualified_expenses": "10000",
        "total_wages": "50000",
        "supply_costs": "5000",
        "contract_research": "20000",
    })
    assert result["status"] == "ANALYZED"
    assert Decimal(result["estimated_credit"]) > 0
    assert result["project"] == "Test Project"


def test_rd_plugin_zero_expenses():
    from rd_plugin.rd_core import run_rd_analysis
    result = run_rd_analysis({"project_name": "Empty", "qualified_expenses": "0"})
    assert result["status"] in ("ANALYZED",)


# ─── API endpoints ────────────────────────────────────────────────────────────

def _create_record(client, auth_headers):
    r = client.post(
        "/tax/records/",
        json={"entity_name": "QRE Corp", "tax_year": 2024, "income": "500000",
              "entity_type": "corporation"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    return r.json()["id"]


def test_api_create_project(client, auth_headers):
    record_id = _create_record(client, auth_headers)
    r = client.post(
        "/rd/projects",
        json={
            "record_id": record_id,
            "project_name": "API Test Project",
            "description": "Building a distributed software algorithm for machine learning encryption",
        },
        headers=auth_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["project_name"] == "API Test Project"
    assert data["activity_type"] is not None
    assert data["is_qualified"] is True


def test_api_list_projects(client, auth_headers):
    record_id = _create_record(client, auth_headers)
    client.post(
        "/rd/projects",
        json={"record_id": record_id, "project_name": "Proj A",
              "description": "Software development for machine learning"},
        headers=auth_headers,
    )
    r = client.get(f"/rd/projects?record_id={record_id}", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_api_add_expense_and_calculate(client, auth_headers):
    record_id = _create_record(client, auth_headers)
    r = client.post(
        "/rd/projects",
        json={"record_id": record_id, "project_name": "Expense Test",
              "description": "Software development algorithm research"},
        headers=auth_headers,
    )
    project_id = r.json()["id"]

    # Add expenses
    client.post(
        f"/rd/projects/{project_id}/expenses",
        json={"category": "wages", "amount": "100000", "description": "Engineer salaries"},
        headers=auth_headers,
    )
    client.post(
        f"/rd/projects/{project_id}/expenses",
        json={"category": "contract_research", "amount": "50000"},
        headers=auth_headers,
    )

    # Calculate
    r = client.post(f"/rd/projects/{project_id}/calculate", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "CALCULATED"
    # total_qre = 100000 + 32500 = 132500; credit = 14% = 18550
    assert Decimal(data["total_qre"]) == Decimal("132500.00")
    assert Decimal(data["estimated_credit"]) == Decimal("18550.00")


def test_api_credit_summary(client, auth_headers):
    record_id = _create_record(client, auth_headers)
    r = client.post(
        "/rd/projects",
        json={"record_id": record_id, "project_name": "Summary Proj",
              "description": "Software algorithm machine learning"},
        headers=auth_headers,
    )
    project_id = r.json()["id"]
    client.post(
        f"/rd/projects/{project_id}/expenses",
        json={"category": "wages", "amount": "80000"},
        headers=auth_headers,
    )
    client.post(f"/rd/projects/{project_id}/calculate", headers=auth_headers)

    r = client.get(f"/rd/summary/{record_id}", headers=auth_headers)
    assert r.status_code == 200
    summary = r.json()
    assert summary["record_id"] == record_id
    assert summary["project_count"] >= 1
    assert Decimal(summary["total_estimated_credit"]) > 0


def test_api_submit_document(client, auth_headers):
    record_id = _create_record(client, auth_headers)
    r = client.post(
        "/rd/projects",
        json={"record_id": record_id, "project_name": "Doc Test",
              "description": "Software research project"},
        headers=auth_headers,
    )
    project_id = r.json()["id"]

    r = client.post(
        f"/rd/projects/{project_id}/documents",
        json={"doc_name": "Technical Report 2024", "doc_type": "technical_report"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["doc_name"] == "Technical Report 2024"
    assert "validation_score" in data


def test_api_delete_project(client, auth_headers):
    record_id = _create_record(client, auth_headers)
    r = client.post(
        "/rd/projects",
        json={"record_id": record_id, "project_name": "Delete Me",
              "description": "software algorithm"},
        headers=auth_headers,
    )
    project_id = r.json()["id"]

    r = client.delete(f"/rd/projects/{project_id}", headers=auth_headers)
    assert r.status_code == 204

    r = client.get(f"/rd/projects/{project_id}", headers=auth_headers)
    assert r.status_code == 404


def test_api_agent_cannot_write_rd(client, agent_headers):
    """Agent role has filings:read but not filings:write."""
    r = client.post(
        "/rd/projects",
        json={"record_id": 1, "project_name": "Blocked", "description": "test"},
        headers=agent_headers,
    )
    assert r.status_code == 403
