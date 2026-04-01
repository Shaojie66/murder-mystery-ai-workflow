"""Landing page email subscription API."""
from datetime import datetime
import uuid
from pathlib import Path
import json

from fastapi import APIRouter

router = APIRouter(prefix="/api/landing", tags=["landing"])

# In-memory store for demo. Replace with database in production.
_subscriptions: dict[str, dict] = {}


@router.post("/subscribe")
async def subscribe(email: str, variant: str = "unknown"):
    """
    Record an email subscription from the landing page.

    In production: save to database, send confirmation email,
    integrate with email marketing tool (e.g., Mailchimp, SendGrid).
    """
    if "@" not in email or "." not in email.split("@")[-1]:
        return {"ok": False, "error": "invalid_email"}

    subscription_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().isoformat()

    _subscriptions[subscription_id] = {
        "id": subscription_id,
        "email": email,
        "variant": variant,
        "subscribed_at": timestamp,
    }

    return {
        "ok": True,
        "id": subscription_id,
        "subscribed_at": timestamp,
    }


@router.get("/subscriptions")
async def list_subscriptions():
    """List all subscriptions (admin only in production)."""
    return {
        "total": len(_subscriptions),
        "subscriptions": list(_subscriptions.values()),
    }
