from app.main import app, get_watchlist, health


def test_health_and_watchlist_do_not_require_market_provider():
    status = health()

    assert status["status"] == "ok"
    assert "Not financial advice" in status["disclaimer"]
    assert "SPY" in get_watchlist()["tickers"]


def test_vercel_service_route_aliases_are_registered():
    paths = {route.path for route in app.routes}

    assert "/api/health" in paths
    assert "/health" in paths
    assert "/api/scores" in paths
    assert "/scores" in paths


def test_ticker_detail_falls_back_when_provider_fails(monkeypatch):
    import app.main as main

    def fail_provider(ticker: str):
        raise RuntimeError("provider offline")

    monkeypatch.setattr(main, "build_ticker_payload", fail_provider)

    payload = main.ticker_detail("SPY")

    assert payload["ticker"] == "SPY"
    assert payload["provider_error"] == "provider offline"
    assert payload["score"]["score"] >= 0
