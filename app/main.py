from fastapi import FastAPI
from tax_capsule.tax_engine import calculate_tax

app = FastAPI(title="WealthBridge Tax Stack - Phase 1")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/tax/calculate")
def tax_calculate(payload: dict):
    return calculate_tax(payload)
