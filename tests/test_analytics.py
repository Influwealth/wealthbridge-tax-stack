"""Wave 7: BI Dashboard, Forecasting, and Credit Optimizer tests."""
import pytest
from decimal import Decimal


# ─── Dashboard — unit tests ───────────────────────────────────────────────────

def test_dashboard_summary_empty(db_session):
    from analytics.dashboard import get_tax_summary
    result = get_tax_summary(db_session, tax_year=9999)
    assert result["record_count"] == 0
    assert result["total_income"] == "0.00"
    assert result["total_tax_due"] == "0.00"


def test_dashboard_summary_with_records(db_session, admin_user):
    from analytics.dashboard import get_tax_summary
    from app.models import TaxRecord
    from decimal import Decimal as D

    db_session.add(TaxRecord(
        entity_name="Dash Corp", tax_year=2024,
        income=D("1000000"), expenses=D("300000"),
        tax_due=D("147000"), entity_type="corporation",
        created_by=admin_user.id,
    ))
    db_session.add(TaxRecord(
        entity_name="Dash Partners", tax_year=2024,
        income=D("500000"), expenses=D("100000"),
        tax_due=D("0"), entity_type="partnership",
        created_by=admin_user.id,
    ))
    db_session.commit()

    result = get_tax_summary(db_session, tax_year=2024)
    assert result["record_count"] >= 2
    assert Decimal(result["total_income"]) >= Decimal("1500000")
    assert "corporation" in result["by_entity_type"]
    assert "partnership" in result["by_entity_type"]


def test_dashboard_entity_history(db_session, admin_user):
    from analytics.dashboard import get_entity_dashboard
    from app.models import TaxRecord
    from decimal import Decimal as D

    for year, income in [(2022, D("400000")), (2023, D("600000")), (2024, D("800000"))]:
        db_session.add(TaxRecord(
            entity_name="History Corp", tax_year=year,
            income=income, expenses=D("100000"),
            tax_due=income * D("0.21"), entity_type="corporation",
            created_by=admin_user.id,
        ))
    db_session.commit()

    result = get_entity_dashboard(db_session, "History Corp")
    assert result["year_count"] >= 3
    assert Decimal(result["total_tax_paid"]) > 0


def test_dashboard_entity_not_found(db_session):
    from analytics.dashboard import get_entity_dashboard
    result = get_entity_dashboard(db_session, "Nonexistent Entity XYZ")
    assert result["year_count"] == 0


def test_dashboard_rd_credits(db_session, admin_user):
    from analytics.dashboard import get_rd_credit_dashboard
    from app.models import TaxRecord, RDProject
    from decimal import Decimal as D

    record = TaxRecord(
        entity_name="RD Dash Corp", tax_year=2024,
        income=D("500000"), expenses=D("100000"),
        tax_due=D("84000"), entity_type="corporation",
        created_by=admin_user.id,
    )
    db_session.add(record)
    db_session.flush()

    db_session.add(RDProject(
        record_id=record.id,
        project_name="Test Project",
        is_qualified=True,
        total_qre=D("100000"),
        estimated_credit=D("14000"),
    ))
    db_session.commit()

    result = get_rd_credit_dashboard(db_session)
    assert result["project_count"] >= 1
    assert Decimal(result["total_estimated_credit"]) >= Decimal("14000")


# ─── Forecasting — unit tests ─────────────────────────────────────────────────

def test_forecast_insufficient_data(db_session):
    from analytics.forecasting import forecast_tax_liability
    result = forecast_tax_liability(db_session, "No Such Entity", forecast_years=3)
    assert result["method"] == "insufficient_data"
    assert result["projections"] == []


def test_forecast_linear_trend(db_session, admin_user):
    from analytics.forecasting import forecast_tax_liability
    from app.models import TaxRecord
    from decimal import Decimal as D

    for year, income in [(2022, D("500000")), (2023, D("600000")), (2024, D("700000"))]:
        db_session.add(TaxRecord(
            entity_name="Trend Corp", tax_year=year,
            income=income, expenses=D("100000"),
            tax_due=(income - D("100000")) * D("0.21"),
            entity_type="corporation", created_by=admin_user.id,
        ))
    db_session.commit()

    result = forecast_tax_liability(db_session, "Trend Corp", forecast_years=2)
    assert result["method"] == "linear_trend"
    assert len(result["projections"]) == 2
    # Income should be growing year over year (trend = +100k/yr)
    p1 = Decimal(result["projections"][0]["projected_income"])
    p2 = Decimal(result["projections"][1]["projected_income"])
    assert p2 > p1


def test_forecast_manual_growth_rate(db_session, admin_user):
    from analytics.forecasting import forecast_tax_liability
    from app.models import TaxRecord
    from decimal import Decimal as D

    db_session.add(TaxRecord(
        entity_name="Growth Corp", tax_year=2024,
        income=D("1000000"), expenses=D("200000"),
        tax_due=D("168000"), entity_type="corporation", created_by=admin_user.id,
    ))
    db_session.commit()

    result = forecast_tax_liability(
        db_session, "Growth Corp", forecast_years=1, growth_rate_override=D("0.10")
    )
    assert result["method"] == "manual_growth_rate"
    # 10% of 1,000,000 = 100,000 growth
    p = result["projections"][0]
    assert Decimal(p["projected_income"]) == Decimal("1100000.00")


def test_cashflow_quarterly_schedule(db_session, admin_user):
    from analytics.forecasting import forecast_cashflow
    from app.models import TaxRecord
    from decimal import Decimal as D

    db_session.add(TaxRecord(
        entity_name="QFlow Corp", tax_year=2023,
        income=D("500000"), expenses=D("100000"),
        tax_due=D("84000"), entity_type="corporation", created_by=admin_user.id,
    ))
    db_session.commit()

    result = forecast_cashflow(db_session, "QFlow Corp", tax_year=2024, quarterly=True)
    assert len(result["quarterly_schedule"]) == 4
    assert result["safe_harbor_annual"] == "84000.00"
    # Each quarter = 84000 / 4 = 21000
    assert result["safe_harbor_quarterly"] == "21000.00"
    assert result["authority"] == "IRC §6654"


def test_cashflow_no_prior_year(db_session):
    from analytics.forecasting import forecast_cashflow
    result = forecast_cashflow(db_session, "New Entity XYZ", tax_year=2024)
    assert result["prior_year_tax"] == "0.00"
    assert result["safe_harbor_quarterly"] == "0.00"


# ─── Credit Optimizer — unit tests ───────────────────────────────────────────

def test_optimizer_rd_credit():
    from analytics.credit_optimizer import optimize_credits
    result = optimize_credits(
        income=Decimal("1000000"),
        expenses=Decimal("300000"),
        entity_type="corporation",
        total_qre=Decimal("200000"),
        estimated_rd_credit=Decimal("28000"),
    )
    strategies = {o["strategy"] for o in result["opportunities"]}
    assert any("R&D" in s for s in strategies)
    assert Decimal(result["total_potential_savings"]) >= Decimal("28000")


def test_optimizer_section_179():
    from analytics.credit_optimizer import optimize_credits
    result = optimize_credits(
        income=Decimal("500000"),
        expenses=Decimal("100000"),
        entity_type="corporation",
        asset_purchases=Decimal("200000"),
    )
    strategies = {o["strategy"] for o in result["opportunities"]}
    assert any("179" in s for s in strategies)


def test_optimizer_qbi_partnership():
    from analytics.credit_optimizer import optimize_credits
    result = optimize_credits(
        income=Decimal("300000"),
        expenses=Decimal("50000"),
        entity_type="partnership",
    )
    strategies = {o["strategy"] for o in result["opportunities"]}
    assert any("199A" in s or "QBI" in s for s in strategies)


def test_optimizer_no_opportunities():
    from analytics.credit_optimizer import optimize_credits
    result = optimize_credits(
        income=Decimal("100000"),
        expenses=Decimal("100000"),
        entity_type="corporation",
    )
    # Zero taxable income → no meaningful opportunities
    assert Decimal(result["taxable_income"]) == Decimal("0")


def test_optimizer_sorted_by_savings():
    from analytics.credit_optimizer import optimize_credits
    result = optimize_credits(
        income=Decimal("2000000"),
        expenses=Decimal("500000"),
        entity_type="corporation",
        total_qre=Decimal("500000"),
        estimated_rd_credit=Decimal("70000"),
        asset_purchases=Decimal("300000"),
    )
    savings = [Decimal(o["estimated_savings"]) for o in result["opportunities"]]
    assert savings == sorted(savings, reverse=True)


def test_optimizer_has_disclaimer():
    from analytics.credit_optimizer import optimize_credits
    result = optimize_credits(
        income=Decimal("100000"), expenses=Decimal("0"), entity_type="corporation"
    )
    assert "disclaimer" in result
    assert len(result["disclaimer"]) > 10


# ─── API endpoints ────────────────────────────────────────────────────────────

def test_api_dashboard_summary(client, auth_headers):
    r = client.get("/analytics/dashboard/summary", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "record_count" in data
    assert "total_income" in data


def test_api_dashboard_summary_by_year(client, auth_headers):
    # Create a record first
    client.post(
        "/tax/records/",
        json={"entity_name": "Analytics Co", "tax_year": 2024, "income": "300000",
              "entity_type": "corporation"},
        headers=auth_headers,
    )
    r = client.get("/analytics/dashboard/summary?tax_year=2024", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["record_count"] >= 1


def test_api_dashboard_entity(client, auth_headers):
    client.post(
        "/tax/records/",
        json={"entity_name": "Entity Dash Corp", "tax_year": 2024, "income": "200000",
              "entity_type": "corporation"},
        headers=auth_headers,
    )
    r = client.get("/analytics/dashboard/entity/Entity Dash Corp", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["entity_name"] == "Entity Dash Corp"
    assert data["year_count"] >= 1


def test_api_dashboard_entity_not_found(client, auth_headers):
    r = client.get("/analytics/dashboard/entity/NoSuchEntity999", headers=auth_headers)
    assert r.status_code == 404


def test_api_forecast_tax_liability(client, auth_headers):
    client.post(
        "/tax/records/",
        json={"entity_name": "Forecast Corp", "tax_year": 2024, "income": "500000",
              "entity_type": "corporation"},
        headers=auth_headers,
    )
    r = client.post(
        "/analytics/forecast/tax-liability",
        json={"entity_name": "Forecast Corp", "forecast_years": 2},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "projections" in data


def test_api_forecast_cashflow(client, auth_headers):
    client.post(
        "/tax/records/",
        json={"entity_name": "Cashflow Corp", "tax_year": 2023, "income": "600000",
              "entity_type": "corporation"},
        headers=auth_headers,
    )
    r = client.post(
        "/analytics/forecast/cashflow",
        json={"entity_name": "Cashflow Corp", "tax_year": 2024},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["quarterly_schedule"]) == 4


def test_api_optimize_record(client, auth_headers):
    r = client.post(
        "/tax/records/",
        json={"entity_name": "Opt Corp", "tax_year": 2024, "income": "1000000",
              "entity_type": "corporation"},
        headers=auth_headers,
    )
    record_id = r.json()["id"]

    r = client.post(
        f"/analytics/optimize/{record_id}",
        json={"record_id": record_id, "asset_purchases": "500000"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "opportunities" in data
    assert "disclaimer" in data


def test_api_optimize_record_not_found(client, auth_headers):
    r = client.post(
        "/analytics/optimize/99999",
        json={"record_id": 99999},
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_api_analytics_requires_auth(client):
    r = client.get("/analytics/dashboard/summary")
    assert r.status_code == 401


def test_api_rd_dashboard(client, auth_headers):
    r = client.get("/analytics/dashboard/rd", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "project_count" in data
    assert "total_qre" in data
