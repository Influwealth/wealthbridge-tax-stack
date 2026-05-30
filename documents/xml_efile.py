"""
IRS XML e-file stubs for Form 1120 and Form 1065.
Generates MeF (Modernized e-File) schema-compliant XML stubs.
Schema reference: IRS Publication 4164 / MeF Schemas.
Note: These are structural stubs — full MeF submission requires IRS ERO credentials,
taxpayer TIN, and schema validation against the official XSD.
"""
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Any


def _pretty_xml(root: ET.Element) -> str:
    """Return indented XML string."""
    raw = ET.tostring(root, encoding="unicode", xml_declaration=False)
    return minidom.parseString(raw).toprettyxml(indent="  ")


def generate_1120_xml(form_data: dict) -> str:
    """
    Generate MeF-style XML stub for Form 1120 (US Corporation Income Tax Return).
    """
    root = ET.Element("Return")
    root.set("xmlns", "http://www.irs.gov/efile")
    root.set("returnVersion", "2023v5.0")
    root.set("binaryAttachmentCount", "0")

    # ReturnHeader
    header = ET.SubElement(root, "ReturnHeader")
    header.set("binaryAttachmentCount", "0")
    ET.SubElement(header, "ReturnTs").text = _iso_ts()
    ET.SubElement(header, "TaxPeriodEndDt").text = f"{form_data.get('tax_year', 2024)}-12-31"
    ET.SubElement(header, "ReturnTypeCd").text = "1120"

    filer = ET.SubElement(header, "Filer")
    ET.SubElement(filer, "EIN").text = "00-0000000"  # placeholder
    ET.SubElement(filer, "BusinessNameLine1Txt").text = str(
        form_data.get("corporation_name", "")
    )

    # ReturnData
    data = ET.SubElement(root, "ReturnData")
    data.set("documentCount", "1")

    irs1120 = ET.SubElement(data, "IRS1120")
    irs1120.set("documentName", "IRS1120")
    ET.SubElement(irs1120, "GrossReceiptsAmt").text = str(
        form_data.get("line_1a_gross_receipts", "0")
    )
    ET.SubElement(irs1120, "TotalDeductionsAmt").text = str(
        form_data.get("line_26_total_deductions", "0")
    )
    ET.SubElement(irs1120, "TaxableIncomeAmt").text = str(
        form_data.get("line_28_taxable_income", "0")
    )
    ET.SubElement(irs1120, "TotalTaxAmt").text = str(
        form_data.get("line_31_total_tax", "0")
    )

    xml_str = _pretty_xml(root)
    return xml_str


def generate_1065_xml(form_data: dict) -> str:
    """
    Generate MeF-style XML stub for Form 1065 (US Return of Partnership Income).
    """
    root = ET.Element("Return")
    root.set("xmlns", "http://www.irs.gov/efile")
    root.set("returnVersion", "2023v4.0")

    header = ET.SubElement(root, "ReturnHeader")
    ET.SubElement(header, "ReturnTs").text = _iso_ts()
    ET.SubElement(header, "TaxPeriodEndDt").text = f"{form_data.get('tax_year', 2024)}-12-31"
    ET.SubElement(header, "ReturnTypeCd").text = "1065"

    filer = ET.SubElement(header, "Filer")
    ET.SubElement(filer, "EIN").text = "00-0000000"
    ET.SubElement(filer, "BusinessNameLine1Txt").text = str(
        form_data.get("partnership_name", "")
    )

    data = ET.SubElement(root, "ReturnData")
    irs1065 = ET.SubElement(data, "IRS1065")
    irs1065.set("documentName", "IRS1065")
    ET.SubElement(irs1065, "GrossReceiptsAmt").text = str(
        form_data.get("line_1a_gross_receipts", "0")
    )
    ET.SubElement(irs1065, "TotalDeductionsAmt").text = str(
        form_data.get("line_22_total_deductions", "0")
    )
    ET.SubElement(irs1065, "OrdinaryBusinessIncomeAmt").text = str(
        form_data.get("line_22_ordinary_business_income", "0")
    )
    ET.SubElement(irs1065, "EntityLevelTaxAmt").text = "0"

    return _pretty_xml(root)


def _iso_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


from datetime import datetime, timezone  # noqa: E402 (re-import at bottom for clarity)
