"""Wave 3: PDF + XML e-file + document vault tests."""
import json
import pytest
from decimal import Decimal
from documents.pdf_filler import fill_form_pdf
from documents.xml_efile import generate_1120_xml, generate_1065_xml
from documents.vault import store_document, retrieve_document, validate_document, delete_document
from irs_forms.base import FormRecord
from irs_forms.form_1120 import generate_1120
from irs_forms.form_1065 import generate_1065


# ─── PDF filler ──────────────────────────────────────────────────────────────

def test_pdf_filler_returns_bytes():
    data = {
        "form": "1120",
        "corporation_name": "Test Corp",
        "tax_year": 2024,
        "line_31_total_tax": "21000.00",
    }
    pdf_bytes = fill_form_pdf(data)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert b"%%EOF" in pdf_bytes


def test_pdf_filler_contains_form_data():
    data = {"form": "TEST", "corporation_name": "My Company", "tax_year": 2024}
    pdf_bytes = fill_form_pdf(data)
    # Form data should appear in the PDF stream content
    assert b"My Company" in pdf_bytes or b"corporation_name" in pdf_bytes


def test_pdf_filler_unicode_safety():
    data = {"form": "W-2", "employer_name": "Acme & Sons (LLC)", "tax_year": 2024}
    pdf_bytes = fill_form_pdf(data)
    assert pdf_bytes.startswith(b"%PDF")


# ─── XML e-file ──────────────────────────────────────────────────────────────

def test_xml_1120_structure():
    rec = FormRecord("Alpha Corp", 2024, Decimal("1000000"), Decimal("300000"), "corporation")
    form_data = generate_1120(rec)
    xml_str = generate_1120_xml(form_data)
    assert "<?xml" in xml_str
    assert "IRS1120" in xml_str
    assert "ReturnHeader" in xml_str
    assert "700000" in xml_str  # taxable_income


def test_xml_1065_structure():
    rec = FormRecord("Beta Partners", 2024, Decimal("500000"), Decimal("100000"), "partnership")
    form_data = generate_1065(rec)
    xml_str = generate_1065_xml(form_data)
    assert "IRS1065" in xml_str
    assert "ReturnTypeCd" in xml_str
    assert "400000" in xml_str  # ordinary_business_income


# ─── Vault store/retrieve/validate/delete ────────────────────────────────────

def test_vault_store_and_retrieve(tmp_path, monkeypatch):
    monkeypatch.setattr("documents.vault.VAULT_DIR", tmp_path)
    content = b"test document content"
    meta = store_document(999, "1120", "pdf", content)
    assert meta["size_bytes"] == len(content)
    assert "checksum_sha256" in meta

    retrieved = retrieve_document(999, "1120", "pdf")
    assert retrieved == content


def test_vault_validate_ok(tmp_path, monkeypatch):
    monkeypatch.setattr("documents.vault.VAULT_DIR", tmp_path)
    content = b"valid document"
    store_document(888, "1065", "json", content)
    result = validate_document(888, "1065", "json")
    assert result["valid"] is True


def test_vault_validate_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr("documents.vault.VAULT_DIR", tmp_path)
    result = validate_document(777, "1120", "pdf")
    assert result["valid"] is False


def test_vault_delete(tmp_path, monkeypatch):
    monkeypatch.setattr("documents.vault.VAULT_DIR", tmp_path)
    content = b"to be deleted"
    store_document(666, "w2", "pdf", content)
    deleted = delete_document(666, "w2", "pdf")
    assert deleted is True
    assert retrieve_document(666, "w2", "pdf") is None


def test_vault_delete_nonexistent(tmp_path, monkeypatch):
    monkeypatch.setattr("documents.vault.VAULT_DIR", tmp_path)
    assert delete_document(555, "941", "xml") is False


# ─── API: document endpoints ─────────────────────────────────────────────────

def test_api_generate_json(client, auth_headers):
    r = client.post(
        "/tax/records/",
        json={"entity_name": "Doc Corp", "tax_year": 2024, "income": "500000",
              "entity_type": "corporation"},
        headers=auth_headers,
    )
    record_id = r.json()["id"]

    r = client.post(
        f"/documents/{record_id}/generate/1120?fmt=json",
        headers=auth_headers,
    )
    assert r.status_code == 200
    meta = r.json()
    assert meta["doc_type"] == "1120"
    assert meta["format"] == "json"
    assert meta["size_bytes"] > 0


def test_api_generate_pdf(client, auth_headers):
    r = client.post(
        "/tax/records/",
        json={"entity_name": "PDF Corp", "tax_year": 2024, "income": "200000",
              "entity_type": "corporation"},
        headers=auth_headers,
    )
    record_id = r.json()["id"]

    r = client.post(
        f"/documents/{record_id}/generate/1120?fmt=pdf",
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["format"] == "pdf"


def test_api_generate_xml(client, auth_headers):
    r = client.post(
        "/tax/records/",
        json={"entity_name": "XML Corp", "tax_year": 2024, "income": "300000",
              "entity_type": "corporation"},
        headers=auth_headers,
    )
    record_id = r.json()["id"]

    r = client.post(
        f"/documents/{record_id}/generate/1120?fmt=xml",
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["format"] == "xml"


def test_api_list_documents(client, auth_headers):
    r = client.post(
        "/tax/records/",
        json={"entity_name": "List Corp", "tax_year": 2024, "income": "100000",
              "entity_type": "corporation"},
        headers=auth_headers,
    )
    record_id = r.json()["id"]
    client.post(f"/documents/{record_id}/generate/1120?fmt=json", headers=auth_headers)

    r = client.get(f"/documents/{record_id}/list", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_api_validate_document(client, auth_headers):
    r = client.post(
        "/tax/records/",
        json={"entity_name": "Validate Corp", "tax_year": 2024, "income": "100000",
              "entity_type": "corporation"},
        headers=auth_headers,
    )
    record_id = r.json()["id"]
    client.post(f"/documents/{record_id}/generate/1120?fmt=json", headers=auth_headers)

    r = client.get(f"/documents/{record_id}/validate/1120?fmt=json", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["valid"] is True


def test_api_generate_unknown_type(client, auth_headers):
    r = client.post(
        "/tax/records/",
        json={"entity_name": "Bad Form", "tax_year": 2024, "income": "100000"},
        headers=auth_headers,
    )
    record_id = r.json()["id"]
    r = client.post(f"/documents/{record_id}/generate/form9999?fmt=json", headers=auth_headers)
    assert r.status_code == 422
