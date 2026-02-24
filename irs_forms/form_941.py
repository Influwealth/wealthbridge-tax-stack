def generate_941(payroll_data: dict):
    return {
        "form": "941",
        "wages_paid": payroll_data.get("wages"),
        "federal_tax_withheld": payroll_data.get("withheld"),
    }
