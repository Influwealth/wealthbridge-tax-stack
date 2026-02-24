def generate_1120(data: dict):
    return {
        "form": "1120",
        "line_1_gross_receipts": data.get("income"),
        "line_28_taxable_income": data.get("taxable_income"),
        "line_31_total_tax": data.get("tax_due"),
    }
