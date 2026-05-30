import os
import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tax_capsule.utils.logger import get_logger

logger = get_logger("BankIngest")

BANK_DATA_DIR = os.getenv("BANK_DATA_DIR", "/data/bank")


def ingest_bank_transactions(source_path: str = None) -> dict:
    """
    Ingest bank transactions from CSV or JSON files.
    Expected CSV columns: date, description, amount, category (optional)
    Expected JSON: list of {date, description, amount, category?}
    """
    path = Path(source_path or BANK_DATA_DIR)
    transactions = []

    if not path.exists():
        logger.warning(f"Bank data path not found: {path} — returning empty")
        return {"source": str(path), "transaction_count": 0, "transactions": []}

    files = list(path.glob("*.csv")) + list(path.glob("*.json")) if path.is_dir() else [path]

    for file in files:
        try:
            if file.suffix == ".csv":
                with open(file, newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            amount = str(Decimal(row.get("amount", "0")))
                        except InvalidOperation:
                            amount = "0"
                        transactions.append({
                            "date": row.get("date", ""),
                            "description": row.get("description", ""),
                            "amount": amount,
                            "category": row.get("category"),
                        })
            elif file.suffix == ".json":
                with open(file, encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        try:
                            amount = str(Decimal(str(item.get("amount", "0"))))
                        except InvalidOperation:
                            amount = "0"
                        transactions.append({
                            "date": item.get("date", ""),
                            "description": item.get("description", ""),
                            "amount": amount,
                            "category": item.get("category"),
                        })
            logger.info(f"Ingested {file.name}")
        except Exception as e:
            logger.error(f"Error reading {file}: {e}")

    return {
        "source": str(path),
        "transaction_count": len(transactions),
        "transactions": transactions,
    }
