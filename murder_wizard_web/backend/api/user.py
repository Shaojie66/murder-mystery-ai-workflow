"""User identity and analytics API endpoints."""
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
import time

from core.auth import encode_token, decode_token

router = APIRouter(prefix="/api/user", tags=["user"])


def _get_user_id(authorization: Optional[str]) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    return decode_token(token)


class TokenRequest(BaseModel):
    user_id: str


class TokenResponse(BaseModel):
    token: str


@router.post("/auth/token", response_model=TokenResponse)
async def create_token(req: TokenRequest):
    """Issue a JWT for a device/user ID."""
    token = encode_token(req.user_id)
    return TokenResponse(token=token)


@router.get("/me")
async def get_me(authorization: Optional[str] = Header(None)):
    """Get current user identity from JWT."""
    user_id = _get_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return {"user_id": user_id}
