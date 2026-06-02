"""
JWT authentication using stdlib hmac/hashlib (no cryptography package dependency).
Implements HS256 (HMAC-SHA256) per RFC 7519.
"""
import os
import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app import models

SECRET_KEY = os.getenv("SECRET_KEY", "INSECURE_DEFAULT_CHANGE_IN_PRODUCTION")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload["exp"] = int(expire.timestamp())

    header = _b64url_encode(json.dumps({"alg": ALGORITHM, "typ": "JWT"}).encode())
    body = _b64url_encode(json.dumps(payload).encode())
    signing_input = f"{header}.{body}".encode()
    signature = _b64url_encode(
        hmac.new(SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
    )
    return f"{header}.{body}.{signature}"


def _decode_token(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format")
        header_b64, body_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{body_b64}".encode()
        expected_sig = _b64url_encode(
            hmac.new(SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
        )
        if not hmac.compare_digest(expected_sig, sig_b64):
            raise ValueError("Invalid signature")
        payload = json.loads(_b64url_decode(body_b64))
        exp = payload.get("exp")
        if exp and datetime.now(timezone.utc).timestamp() > exp:
            raise ValueError("Token expired")
        return payload
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        raise ValueError(f"Token validation failed: {e}")


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def _try_supabase_jwt(token: str, db: Session) -> Optional[models.User]:
    """
    Attempt to resolve a Supabase JWT to a local User.
    Maps Supabase `email` claim to User.username (email-as-username convention).
    Returns None if Supabase auth is not configured or token is invalid.
    """
    try:
        from supabase.auth import verify_supabase_jwt, extract_supabase_user_info
        claims = verify_supabase_jwt(token)
        if not claims:
            return None
        info = extract_supabase_user_info(claims)
        username = info.get("email") or info.get("sub", "")
        if not username:
            return None
        return db.query(models.User).filter(
            models.User.username == username,
            models.User.is_active == True,
        ).first()
    except Exception:
        return None


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1. Try internal JWT
    try:
        payload = _decode_token(token)
        username: str = payload.get("sub")
        if username:
            user = db.query(models.User).filter(models.User.username == username).first()
            if user and user.is_active:
                return user
    except ValueError:
        pass

    # 2. Try Supabase JWT passthrough
    supabase_user = _try_supabase_jwt(token, db)
    if supabase_user:
        return supabase_user

    raise credentials_exception
