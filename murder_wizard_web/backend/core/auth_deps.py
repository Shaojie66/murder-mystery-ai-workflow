"""Shared FastAPI auth dependencies."""
from typing import Optional

from fastapi import Header, HTTPException

from core.auth import decode_token


async def require_auth(authorization: Optional[str] = Header(None)) -> str:
    """Validate bearer token and return the authenticated user id."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    user_id = decode_token(authorization[7:])
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user_id
