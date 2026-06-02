"""
Supabase JWT verification for hybrid auth.

When SUPABASE_JWT_SECRET is set, the auth dependency will accept both:
  1. Internal HMAC-HS256 JWTs (issued by /auth/token)
  2. Supabase-issued JWTs (from Supabase Auth)

Supabase JWTs are signed with the project's JWT secret (HS256) and carry
standard claims plus a `role` field and optional `email`.
"""
import os
import json
import hmac
import hashlib
import base64
from typing import Optional
from tax_capsule.utils.logger import get_logger

logger = get_logger("SupabaseAuth")

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")


def _b64url_decode(s: str) -> bytes:
    s += "=" * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s)


def verify_supabase_jwt(token: str) -> Optional[dict]:
    """
    Verify a Supabase JWT using SUPABASE_JWT_SECRET.
    Returns claims dict on success, None on failure.
    """
    if not SUPABASE_JWT_SECRET:
        return None

    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected_sig = hmac.new(
            SUPABASE_JWT_SECRET.encode(), signing_input, hashlib.sha256
        ).digest()
        provided_sig = _b64url_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, provided_sig):
            logger.warning("Supabase JWT signature verification failed")
            return None

        claims = json.loads(_b64url_decode(payload_b64))

        import time
        if claims.get("exp", 0) < int(time.time()):
            logger.warning("Supabase JWT expired")
            return None

        return claims

    except Exception as e:
        logger.warning(f"Supabase JWT parse error: {e}")
        return None


def extract_supabase_user_info(claims: dict) -> dict:
    """Extract normalized user info from Supabase JWT claims."""
    return {
        "sub": claims.get("sub", ""),
        "email": claims.get("email", ""),
        "role": claims.get("role", "authenticated"),
        "app_metadata": claims.get("app_metadata", {}),
        "user_metadata": claims.get("user_metadata", {}),
    }
