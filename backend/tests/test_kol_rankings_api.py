from __future__ import annotations

from app.services.kol_performance import KOLPerformanceService
from tests.helpers import seed_kol_performance_history


def _seed_rankings(session_factory) -> None:
    db = session_factory()
    try:
        seed_kol_performance_history(db)
        KOLPerformanceService(db).refresh_kol_performance()
    finally:
        db.close()


def test_get_kol_rankings_returns_sorted_kols(api_client, session_factory) -> None:
    _seed_rankings(session_factory)

    response = api_client.get("/api/kols/rankings?limit=10&include_insufficient=false")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    assert payload["items"][0]["handle"] == "alpha_calls"
    assert payload["items"][-1]["handle"] == "beta_calls"
    assert "methodology" in payload


def test_get_kol_track_record_returns_score_and_calls(api_client, session_factory) -> None:
    _seed_rankings(session_factory)

    response = api_client.get("/api/kols/alpha_calls/track-record")

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile"]["handle"] == "alpha_calls"
    assert payload["score"]["evaluated_calls"] >= 5
    assert isinstance(payload["recent_calls"], list)
    assert "methodology" in payload
    assert "disclaimer" in payload


def test_empty_rankings_return_graceful_empty_result(api_client) -> None:
    response = api_client.get("/api/kols/rankings")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert "methodology" in payload


def test_refresh_kol_performance_endpoint_runs(api_client, session_factory) -> None:
    db = session_factory()
    try:
        seed_kol_performance_history(db)
    finally:
        db.close()

    response = api_client.post("/api/admin/refresh-kol-performance")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert set(payload) >= {"calls_created", "calls_evaluated", "scores_updated", "warnings"}
