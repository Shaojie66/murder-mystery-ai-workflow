"""批次 D（R11）：留资 JSON 合同、访问数口径；R12：本地单用户边界。"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from murder_wizard_web.backend.main import app
    import api.analytics as A
    import api.landing as L
    A._events.clear()
    L._subscriptions.clear()
    with TestClient(app) as c:
        yield c
    A._events.clear()
    L._subscriptions.clear()


def test_subscribe_accepts_json_body(client):
    r = client.post("/api/landing/subscribe", json={"email": "a@example.com", "variant": "a"})
    assert r.status_code == 200 and r.json()["ok"] is True and r.json()["duplicate"] is False


def test_subscribe_legacy_query_params_still_work(client):
    r = client.post("/api/landing/subscribe?email=q@example.com&variant=b")
    assert r.status_code == 200 and r.json()["ok"] is True


@pytest.mark.parametrize("bad", ["", "no-at", "a@b", "a b@c.com", "@x.com", "x" * 260 + "@a.com"])
def test_invalid_email_is_a_4xx_not_a_200(client, bad):
    r = client.post("/api/landing/subscribe", json={"email": bad})
    assert r.status_code == 422 and r.json()["detail"] == "invalid_email"
    assert client.get("/api/landing/subscriptions").json()["total"] == 0


def test_missing_email_is_422_and_duplicates_count_once(client):
    assert client.post("/api/landing/subscribe", json={}).status_code == 422
    assert client.post("/api/landing/subscribe").status_code == 422
    first = client.post("/api/landing/subscribe", json={"email": "Dup@Example.com"}).json()
    again = client.post("/api/landing/subscribe", json={"email": " dup@example.com "}).json()
    assert again["duplicate"] is True and again["id"] == first["id"]
    body = client.get("/api/landing/subscriptions").json()
    assert body["total"] == 1 and body["persisted"] is False


def _track(client, **kw):
    assert client.post("/api/analytics/track", json=kw).status_code == 200


def test_one_visit_counts_once_and_leave_is_not_a_view(client):
    for _ in range(3):  # StrictMode / 重复挂载 / 重复上报
        _track(client, event="page_view", variant="a", visit_id="v1")
    _track(client, event="page_leave", variant="a", visit_id="v1", duration=4000)
    _track(client, event="page_view", variant="b", visit_id="v2")
    s = client.get("/api/analytics/summary").json()
    assert s["page_views"] == 2 and s["variant_a"] == 1 and s["variant_b"] == 1
    assert s["avg_duration"] == 4000 and s["persisted"] is False


def test_conversion_uses_unique_visits_per_variant(client):
    for i in range(4):
        _track(client, event="page_view", variant="a", visit_id=f"a{i}")
    _track(client, event="page_view", variant="b", visit_id="b0")
    _track(client, event="email_submit", variant="a", visit_id="a0")
    _track(client, event="email_submit", variant="a", visit_id="a0")  # 同一次访问重复提交
    _track(client, event="email_submit", variant="b", visit_id="b0")
    s = client.get("/api/analytics/summary").json()
    assert s["conversion_rate_a"] == 25.0 and s["conversion_rate_b"] == 100.0


def test_events_without_visit_id_still_count_individually(client):
    _track(client, event="page_view", variant="a")
    _track(client, event="page_view", variant="a")
    assert client.get("/api/analytics/summary").json()["page_views"] == 2


def test_frontend_assignment_is_visitor_stable_and_not_ua_based():
    from pathlib import Path
    root = Path(__file__).parent.parent / "murder_wizard_web" / "frontend" / "src"
    page = (root / "landing" / "LandingPage.tsx").read_text(encoding="utf-8")
    assert "userAgent" not in page and "getVisitorId" in page and "assignVariant" in page
    hook = (root / "hooks" / "useAnalytics.ts").read_text(encoding="utf-8")
    assert "page_leave" in hook and "visit_id" in hook
    modal = (root / "landing" / "components" / "Modal.tsx").read_text(encoding="utf-8")
    assert "detail" in modal
