from fastapi import FastAPI, HTTPException
from tax_capsule.tax_engine import calculate_tax
from tax_capsule.utils.schemas import TaxCalculationRequest, TaxResponse
from tax_capsule.utils.logger import get_logger

logger = get_logger("API")
app = FastAPI(title="WealthBridge Tax Stack - Production v1")

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}

@app.post("/tax/calculate", response_model=TaxResponse)
async def tax_calculate(payload: TaxCalculationRequest):
    try:
        result = calculate_tax(payload)
        return result
    except Exception as e:
        logger.error(f"Calculation error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error during calculation")
