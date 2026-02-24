import hmac
import hashlib
import os
from fastapi import FastAPI, Request, HTTPException
from tax_capsule.utils.logger import get_logger

SECRET = os.getenv("OPENWISPR_SECRET", "changeme")
logger = get_logger("OpenWisprRelay")
relay_app = FastAPI(title="OpenWispr Relay")

def verify_signature(payload: bytes, signature: str):
    expected = hmac.new(
        SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@relay_app.post("/relay")
async def handle_relay(request: Request):
    raw = await request.body()
    signature = request.headers.get("X-Signature", "")
    if not verify_signature(raw, signature):
        logger.warning("Invalid signature on relay request")
        raise HTTPException(status_code=401, detail="Invalid signature")
    data = await request.json()
    logger.info(f"Relay received payload: {data}")
    return {"status": "relayed", "data": data}
