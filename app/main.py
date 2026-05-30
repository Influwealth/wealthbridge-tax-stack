import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, tax_records, forms, integrations
from tax_capsule.utils.logger import get_logger

logger = get_logger("API")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("WealthBridge Tax Stack v3 starting up")
    yield
    logger.info("WealthBridge Tax Stack v3 shutting down")


app = FastAPI(
    title="WealthBridge Tax Stack",
    version="3.0.0",
    description="Production tax management API for wealth management firms",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(auth.router)
app.include_router(tax_records.router)
app.include_router(forms.router)
app.include_router(integrations.router)


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "3.0.0"}


@app.post("/tax/calculate")
async def tax_calculate_legacy(payload: dict):
    """Legacy endpoint — kept for backward compatibility."""
    from tax_capsule.tax_engine import calculate_tax
    from tax_capsule.utils.schemas import TaxCalculationRequest
    result = calculate_tax(TaxCalculationRequest(**payload))
    return result
