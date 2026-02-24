def run_rd_analysis(data):
    return {
        "project": data.get("project_name"),
        "qualified_expenses": data.get("qualified_expenses"),
        "status": "ANALYZED"
    }
