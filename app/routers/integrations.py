from fastapi import APIRouter, Depends

from app import models
from app.rbac import require_permission
from agoda_connector.ingest_bank import ingest_bank_transactions
from rd_plugin.rd_core import run_rd_analysis
from manager_sync_agent.sync_managerio import pull_managerio_data
from tax_capsule.utils.schemas import RDAnalysisRequest

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/bank/ingest")
def bank_ingest(_: models.User = Depends(require_permission("expenses:read"))):
    return ingest_bank_transactions()


@router.post("/rd/analyze")
def rd_analyze(
    payload: RDAnalysisRequest,
    _: models.User = Depends(require_permission("expenses:read")),
):
    return run_rd_analysis(payload.model_dump())


@router.get("/managerio/sync")
def managerio_sync(_: models.User = Depends(require_permission("records:read"))):
    return pull_managerio_data()
