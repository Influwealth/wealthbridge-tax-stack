"""
Tool schemas for the Caffeine Agent (Claude Anthropic tool-use format).
"""

TOOL_SCHEMAS = [
    {
        "name": "get_tax_record",
        "description": "Retrieve a specific tax record by ID. Returns entity name, income, expenses, tax due, and entity type.",
        "input_schema": {
            "type": "object",
            "properties": {
                "record_id": {
                    "type": "integer",
                    "description": "The numeric ID of the tax record",
                }
            },
            "required": ["record_id"],
        },
    },
    {
        "name": "list_tax_records",
        "description": "List tax records, optionally filtered by tax year. Returns up to 20 records.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tax_year": {
                    "type": "integer",
                    "description": "Filter by tax year (e.g. 2024)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum records to return (default 10)",
                    "default": 10,
                },
            },
            "required": [],
        },
    },
    {
        "name": "calculate_tax",
        "description": "Calculate estimated tax liability for given income, expenses, and entity type.",
        "input_schema": {
            "type": "object",
            "properties": {
                "income": {
                    "type": "number",
                    "description": "Gross income in USD",
                },
                "expenses": {
                    "type": "number",
                    "description": "Deductible expenses in USD (default 0)",
                    "default": 0,
                },
                "entity_type": {
                    "type": "string",
                    "enum": ["corporation", "partnership", "employer", "sole_proprietor"],
                    "description": "Entity type for rate selection",
                },
            },
            "required": ["income"],
        },
    },
    {
        "name": "get_rd_credit_summary",
        "description": "Get the R&D tax credit summary for all projects associated with a tax record.",
        "input_schema": {
            "type": "object",
            "properties": {
                "record_id": {
                    "type": "integer",
                    "description": "The tax record ID to summarize R&D credits for",
                }
            },
            "required": ["record_id"],
        },
    },
    {
        "name": "get_form_data",
        "description": "Generate IRS form data (1120 or 1065) for a tax record without storing it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "record_id": {
                    "type": "integer",
                    "description": "The tax record ID",
                },
                "form_type": {
                    "type": "string",
                    "enum": ["1120", "1065", "941"],
                    "description": "IRS form type to generate",
                },
            },
            "required": ["record_id", "form_type"],
        },
    },
]
