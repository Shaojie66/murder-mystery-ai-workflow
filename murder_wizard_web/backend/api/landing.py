"""Landing page email subscription API (interest signals only).

留邮箱只代表兴趣，不是注册、付费或留存，不要把这里的数字当成付费依据。
数据追加写入 ~/.murder-wizard/landing/subscriptions.jsonl，启动后首次使用时回放；工具不自动删除。
"""
import re
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.jsonl_store import JsonlStore

router = APIRouter(prefix="/api/landing", tags=["landing"])

_subscriptions: dict[str, dict] = {}
_store = JsonlStore("subscriptions.jsonl", "landing-subscription/1")
_loaded = False
_corrupt = 0
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SubscribeRequest(BaseModel):
    email: str
    variant: str = "unknown"


def _ensure_loaded() -> None:
    """首次使用时回放磁盘记录（同邮箱只保留第一条）。"""
    global _loaded, _corrupt
    if _loaded:
        return
    records, _corrupt = _store.replay()
    seen = {s["email"] for s in _subscriptions.values()}
    for r in records:
        email = r.get("email")
        if isinstance(email, str) and email not in seen and r.get("id"):
            seen.add(email)
            _subscriptions[r["id"]] = {k: r[k] for k in ("id", "email", "variant", "subscribed_at") if k in r}
    _loaded = True


def _normalize(email: str) -> str:
    return email.strip().lower()


def _record(email: str, variant: str) -> dict:
    _ensure_loaded()
    email = _normalize(email)
    if len(email) > 254 or not _EMAIL_RE.match(email):
        # 无效邮箱必须是 4xx：前端只看 HTTP 状态，不能把失败当成功
        raise HTTPException(status_code=422, detail="invalid_email")
    for sub in _subscriptions.values():
        if sub["email"] == email:  # 同一邮箱只记一次，不重复计数
            return {"ok": True, "id": sub["id"], "subscribed_at": sub["subscribed_at"], "duplicate": True}
    sub_id = str(uuid.uuid4())[:8]
    ts = datetime.now().isoformat()
    record = {"id": sub_id, "email": email, "variant": variant, "subscribed_at": ts}
    try:
        _store.append(record)  # 先写盘再改内存：写失败不能返回"已记录"
    except OSError:
        raise HTTPException(status_code=503, detail="storage_unavailable")
    _subscriptions[sub_id] = record
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
    _ensure_loaded()
    return {
        "total": len(_subscriptions),
        "persisted": True,
        "corrupt_lines": _corrupt,
        "subscriptions": list(_subscriptions.values()),
    }
