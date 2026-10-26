"""批次 D（R11）：留资 JSON 合同、访问数口径；R12：本地单用户边界。"""
import pytest
from fastapi.testclient import TestClient


def _reset(A, L):
    A._events.clear(); L._subscriptions.clear()
    A._loaded = L._loaded = False
    A._corrupt = L._corrupt = 0


@pytest.fixture
def client(tmp_path, monkeypatch):
    """持久化目录指向临时目录：测试从不写真实的 ~/.murder-wizard。"""
    from murder_wizard_web.backend.main import app
    import core.jsonl_store as J
    import api.analytics as A
    import api.landing as L
    monkeypatch.setattr(J, "landing_dir", lambda: tmp_path / "landing")
    _reset(A, L)
    with TestClient(app) as c:
        yield c
    _reset(A, L)


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
    assert body["total"] == 1 and body["persisted"] is True


def _track(client, **kw):
    assert client.post("/api/analytics/track", json=kw).status_code == 200


def test_one_visit_counts_once_and_leave_is_not_a_view(client):
    for _ in range(3):  # StrictMode / 重复挂载 / 重复上报
        _track(client, event="page_view", variant="a", visit_id="v1")
    _track(client, event="page_leave", variant="a", visit_id="v1", duration=4000)
    _track(client, event="page_view", variant="b", visit_id="v2")
    s = client.get("/api/analytics/summary").json()
    assert s["page_views"] == 2 and s["variant_a"] == 1 and s["variant_b"] == 1
    assert s["avg_duration"] == 4000 and s["persisted"] is True


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


# ── 持久化：追加写 JSONL、启动回放、不自动删除 ─────────────────────────

def _restart():
    import api.analytics as A
    import api.landing as L
    _reset(A, L)  # 模拟进程重启：内存清空，下次使用时回放磁盘


def test_subscriptions_survive_restart_and_dedupe_on_replay(client, tmp_path):
    client.post("/api/landing/subscribe", json={"email": "keep@example.com", "variant": "a"})
    client.post("/api/landing/subscribe", json={"email": "KEEP@example.com"})  # 重复，不再写盘
    f = tmp_path / "landing" / "subscriptions.jsonl"
    assert len(f.read_text(encoding="utf-8").splitlines()) == 1
    _restart()
    body = client.get("/api/landing/subscriptions").json()
    assert body["total"] == 1 and body["subscriptions"][0]["email"] == "keep@example.com"
    again = client.post("/api/landing/subscribe", json={"email": "keep@example.com"}).json()
    assert again["duplicate"] is True and len(f.read_text(encoding="utf-8").splitlines()) == 1


def test_events_survive_restart_and_summary_keeps_visit_dedupe(client):
    for _ in range(2):
        _track(client, event="page_view", variant="a", visit_id="v1")
    _track(client, event="email_submit", variant="a", visit_id="v1")
    before = client.get("/api/analytics/summary").json()
    _restart()
    after = client.get("/api/analytics/summary").json()
    assert after["page_views"] == before["page_views"] == 1
    assert after["conversion_rate_a"] == before["conversion_rate_a"] == 100.0


def test_file_is_append_only_private_and_never_deleted(client, tmp_path):
    f = tmp_path / "landing" / "events.jsonl"
    _track(client, event="cta_click", variant="a", visit_id="x")
    first = f.read_bytes()
    _track(client, event="cta_click", variant="a", visit_id="y")
    assert f.read_bytes().startswith(first) and f.read_bytes() != first  # 只追加，不改写
    import stat
    assert stat.S_IMODE(f.stat().st_mode) == 0o600
    assert stat.S_IMODE(f.parent.stat().st_mode) == 0o700
    assert '"schema": "landing-event/1"' in first.decode("utf-8")
    _restart()
    client.get("/api/analytics/summary")
    assert f.exists()  # 回放不会删除或改写


def test_corrupt_lines_are_skipped_and_counted_not_fatal(client, tmp_path):
    d = tmp_path / "landing"
    d.mkdir()
    (d / "subscriptions.jsonl").write_text(
        '{"schema": "landing-subscription/1", "id": "s1", "email": "ok@example.com", "variant": "a", "subscribed_at": "t"}\n'
        "{坏行\n"
        '{"schema": "other/9", "id": "s2", "email": "x@example.com"}\n'
        "\n", encoding="utf-8")
    body = client.get("/api/landing/subscriptions").json()
    assert body["total"] == 1 and body["corrupt_lines"] == 2
    assert (d / "subscriptions.jsonl").read_text(encoding="utf-8").count("\n") == 4  # 原文件未被改动


def test_write_failure_is_503_and_not_remembered(client, monkeypatch):
    import core.jsonl_store as J
    def boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(J.os, "write", boom)
    r = client.post("/api/landing/subscribe", json={"email": "fail@example.com"})
    assert r.status_code == 503 and r.json()["detail"] == "storage_unavailable"
    assert client.get("/api/landing/subscriptions").json()["total"] == 0
    assert client.post("/api/analytics/track", json={"event": "page_view", "variant": "a"}).status_code == 503
    monkeypatch.undo()
    assert client.post("/api/landing/subscribe", json={"email": "fail@example.com"}).status_code == 200
