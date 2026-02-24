def validate_required_fields(data: dict, required_fields: list):
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")
    return True
