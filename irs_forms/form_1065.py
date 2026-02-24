def generate_1065(data: dict):
    return {
        "form": "1065",
        "total_income": data.get("income"),
        "ordinary_business_income": data.get("taxable_income"),
    }
