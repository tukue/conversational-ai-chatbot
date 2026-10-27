from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import httpx
from fastapi.testclient import TestClient

from src.llm_proxy import Settings, create_app
from src.proxy_analytics import AnalyticsStore


def test_atomic_updates_across_store_instances(tmp_path):
    path = str(tmp_path / "analytics.db")
    first, second = AnalyticsStore(path), AnalyticsStore(path)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda i: (first if i % 2 else second).record({"requests": 1, "prompt_tokens": 3}), range(100)))
    assert AnalyticsStore(path).report(7)["totals"] == {"requests": 100, "prompt_tokens": 300}


def test_retention(tmp_path):
    store = AnalyticsStore(str(tmp_path / "analytics.db"), retention_days=2)
    old = (datetime.now(timezone.utc).date() - timedelta(days=2)).isoformat()
    with store.connect() as db:
        db.execute("INSERT INTO daily_metrics VALUES (?, 'requests', 100)", (old,))
    store.record({"requests": 1})
    assert store.report(2)["totals"] == {"requests": 1}
    with store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM daily_metrics WHERE day = ?", (old,)).fetchone()[0] == 0


def test_restart_reporting_and_storage_failure(tmp_path, monkeypatch):
    path = tmp_path / "usage.db"
    settings = Settings("client", "admin", "provider", "https://provider.test/chat", ("test-model",),
                        analytics_db=str(path))

    def upstream(request):
        return httpx.Response(200, json={
            "choices": [{"message": {"role": "assistant", "content": "Your order is on its way."}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8},
        })

    def send(client):
        return client.post("/v1/chat/completions", headers={"Authorization": "Bearer client"},
                           json={"model": "test-model", "messages": [{"role": "user", "content": "Where is my order?"}]})

    with TestClient(create_app(settings, httpx.MockTransport(upstream))) as client:
        assert send(client).status_code == 200
    with TestClient(create_app(settings, httpx.MockTransport(upstream))) as client:
        headers = {"Authorization": "Bearer admin"}
        assert client.get("/analytics/history").status_code == 401
        assert client.get("/analytics/history?days=91", headers=headers).status_code == 422
        report = client.get("/analytics/history", headers=headers).json()
        assert report["totals"]["prompt_tokens"] == 12
        assert report["totals"]["allowed"] == 1
        assert "Where is my order" not in str(report)

        def broken(metrics):
            raise OSError("private database path")

        monkeypatch.setattr(client.app.state.analytics_store, "record", broken)
        assert send(client).status_code == 200
        assert client.get("/analytics", headers=headers).json()["analytics_write_errors"] == 1
        monkeypatch.setattr(client.app.state.analytics_store, "report", broken)
        result = client.get("/analytics/history", headers=headers)
        assert result.status_code == 503
        assert "private database path" not in result.text
    assert b"Where is my order" not in path.read_bytes()
