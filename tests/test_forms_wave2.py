"""Wave 2: New IRS form generator tests."""
import pytest
from decimal import Decimal
from irs_forms.base import FormRecord, validate_record, FormValidationError
from irs_forms.form_schedule_c import generate_schedule_c
from irs_forms.form_w2 import generate_w2
from irs_forms.form_1099_nec import generate_1099_nec
from irs_forms.state.ny_it201 import generate_ny_it201
from irs_forms.state.ca_540 import generate_ca_540
from irs_forms.state.tx_franchise import generate_tx_franchise


# ─── base validation ────────────────────────────────────────────────────────

def test_validate_record_ok():
    r = FormRecord("Acme", 2024, Decimal("100000"), Decimal("20000"), "sole_proprietor")
    validate_record(r, expected_entity_type="sole_proprietor")  # no exception


def test_validate_record_wrong_entity_type():
    r = FormRecord("Acme", 2024, Decimal("100000"), entity_type="partnership")
    with pytest.raises(FormValidationError, match="entity_type"):
        validate_record(r, expected_entity_type="sole_proprietor")


def test_validate_record_missing_name():
    r = FormRecord("", 2024, Decimal("100000"), entity_type="sole_proprietor")
    with pytest.raises(FormValidationError, match="entity_name"):
        validate_record(r, expected_entity_type="sole_proprietor")


# ─── Schedule C ─────────────────────────────────────────────────────────────

def test_schedule_c_basic():
    r = FormRecord("Solo Inc", 2024, Decimal("80000"), Decimal("20000"), "sole_proprietor")
    result = generate_schedule_c(r)
    assert result["form"] == "Schedule C"
    assert result["line_31_net_profit"] == "60000"
    assert Decimal(result["estimated_se_tax"]) > Decimal("0")


def test_schedule_c_net_loss():
    r = FormRecord("Loss LLC", 2024, Decimal("10000"), Decimal("50000"), "sole_proprietor")
    result = generate_schedule_c(r)
    assert result["line_31_net_profit"] == "0"
    assert result["line_31_net_loss"] == "40000"


def test_schedule_c_wrong_type():
    r = FormRecord("Corp", 2024, Decimal("100000"), entity_type="corporation")
    with pytest.raises(FormValidationError):
        generate_schedule_c(r)


# ─── W-2 ────────────────────────────────────────────────────────────────────

def test_w2_basic():
    r = FormRecord("MegaCorp", 2024, Decimal("100000"), entity_type="employee")
    result = generate_w2(r)
    assert result["form"] == "W-2"
    assert result["box_1_wages_tips"] == "100000"
    assert Decimal(result["box_4_ss_withheld"]) > Decimal("0")
    assert Decimal(result["box_6_medicare_withheld"]) > Decimal("0")


def test_w2_ss_wage_base_cap():
    """SS wages are capped at $168,600 (2024 base)."""
    r = FormRecord("HighPay Corp", 2024, Decimal("300000"), entity_type="employee")
    result = generate_w2(r)
    assert Decimal(result["box_3_ss_wages"]) == Decimal("168600")
    assert Decimal(result["additional_medicare_tax"]) > Decimal("0")


def test_w2_wrong_type():
    r = FormRecord("Solo", 2024, Decimal("50000"), entity_type="sole_proprietor")
    with pytest.raises(FormValidationError):
        generate_w2(r)


# ─── 1099-NEC ───────────────────────────────────────────────────────────────

def test_1099_nec_above_threshold():
    r = FormRecord("Freelancer Co", 2024, Decimal("5000"), entity_type="contractor")
    result = generate_1099_nec(r)
    assert result["form"] == "1099-NEC"
    assert result["filing_required"] is True
    assert result["box_4_federal_withheld"] == "0.00"


def test_1099_nec_below_threshold():
    r = FormRecord("Micro LLC", 2024, Decimal("500"), entity_type="contractor")
    result = generate_1099_nec(r)
    assert result["filing_required"] is False
    assert result["below_reporting_threshold"] is True


def test_1099_nec_backup_withholding():
    r = FormRecord("No TIN LLC", 2024, Decimal("10000"), entity_type="contractor")
    result = generate_1099_nec(r, apply_backup_withholding=True)
    assert Decimal(result["box_4_federal_withheld"]) == Decimal("2400.00")


# ─── State forms ────────────────────────────────────────────────────────────

def test_ny_it201_stub():
    r = FormRecord("NY Corp", 2024, Decimal("200000"), Decimal("50000"))
    result = generate_ny_it201(r)
    assert result["state"] == "NY"
    assert result["status"] == "STUB"
    assert Decimal(result["estimated_ny_tax"]) > Decimal("0")


def test_ca_540_stub():
    r = FormRecord("CA Corp", 2024, Decimal("300000"), Decimal("100000"))
    result = generate_ca_540(r)
    assert result["state"] == "CA"
    assert Decimal(result["estimated_sdi"]) > Decimal("0")


def test_tx_franchise_no_tax_due():
    r = FormRecord("Small TX LLC", 2024, Decimal("1000000"))
    result = generate_tx_franchise(r)
    assert result["state"] == "TX"
    assert result["no_tax_due_applies"] is True


def test_tx_franchise_tax_due():
    r = FormRecord("Big TX Corp", 2024, Decimal("50000000"), Decimal("10000000"))
    result = generate_tx_franchise(r)
    assert result["no_tax_due_applies"] is False
    assert Decimal(result["estimated_tax_due"]) > Decimal("0")


# ─── API: new form endpoints ─────────────────────────────────────────────────

def test_api_schedule_c(client, auth_headers, db_session):
    r = client.post(
        "/tax/records/",
        json={"entity_name": "Solo Biz", "tax_year": 2024, "income": "80000",
              "expenses": "20000", "entity_type": "sole_proprietor"},
        headers=auth_headers,
    )
    record_id = r.json()["id"]
    r = client.post(f"/forms/schedule-c/{record_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["form"] == "Schedule C"


def test_api_w2(client, auth_headers):
    r = client.post(
        "/tax/records/",
        json={"entity_name": "Employer Inc", "tax_year": 2024,
              "income": "100000", "entity_type": "employee"},
        headers=auth_headers,
    )
    record_id = r.json()["id"]
    r = client.post(f"/forms/w2/{record_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["form"] == "W-2"


def test_api_1099_nec(client, auth_headers):
    r = client.post(
        "/tax/records/",
        json={"entity_name": "Contractor Co", "tax_year": 2024,
              "income": "15000", "entity_type": "contractor"},
        headers=auth_headers,
    )
    record_id = r.json()["id"]
    r = client.post(f"/forms/1099-nec/{record_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["form"] == "1099-NEC"


def test_api_state_ny(client, auth_headers):
    r = client.post(
        "/tax/records/",
        json={"entity_name": "NY Biz", "tax_year": 2024, "income": "500000"},
        headers=auth_headers,
    )
    record_id = r.json()["id"]
    r = client.post(f"/forms/state/ny/it201/{record_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["state"] == "NY"


def test_api_state_unknown(client, auth_headers):
    r = client.post(
        "/tax/records/",
        json={"entity_name": "Unknown State", "tax_year": 2024, "income": "100000"},
        headers=auth_headers,
    )
    record_id = r.json()["id"]
    r = client.post(f"/forms/state/vt/it111/{record_id}", headers=auth_headers)
    assert r.status_code == 404
