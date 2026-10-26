"""Landing page email subscription API (interest signals only, held in memory).

留邮箱只代表兴趣，不是注册、付费或留存；数据只在内存里，进程重启即丢失。
没有可靠持久化和研究安排之前，不要把这里的数字当成付费依据。
"""
import re
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/landing", tags=["landing"])

_subscriptions: dict[str, dict] = {}
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SubscribeRequest(BaseModel):
    email: str
    variant: str = "unknown"


def _normalize(email: str) -> str:
    return email.strip().lower()


def _record(email: str, variant: str) -> dict:
    email = _normalize(email)
    if len(email) > 254 or not _EMAIL_RE.match(email):
        # 无效邮箱必须是 4xx：前端只看 HTTP 状态，不能把失败当成功
        raise HTTPException(status_code=422, detail="invalid_email")
    for sub in _subscriptions.values():
        if sub["email"] == email:  # 同一邮箱只记一次，不重复计数
            return {"ok": True, "id": sub["id"], "subscribed_at": sub["subscribed_at"], "duplicate": True}
    sub_id = str(uuid.uuid4())[:8]
    ts = datetime.now().isoformat()
    _subscriptions[sub_id] = {"id": sub_id, "email": email, "variant": variant, "subscribed_at": ts}
    return {"ok": True, "id": sub_id, "subscribed_at": ts, "duplicate": False}


@router.post("/subscribe")
async def subscribe(body: Optional[SubscribeRequest] = None, email: Optional[str] = None, variant: str = "unknown"):
    """记录一次留资。接受 JSON 请求体（前端使用）；仍兼容旧的查询参数写法。"""
    if body is not None:
        return _record(body.email, body.variant)
    if email is not None:
        return _record(email, variant)
    raise HTTPException(status_code=422, detail="email_required")


@router.get("/subscriptions")
async def list_subscriptions():
    """List all subscriptions (admin only in production)."""
    return {
        "total": len(_subscriptions),
        "persisted": False,
        "subscriptions": list(_subscriptions.values()),
    }
