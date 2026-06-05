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
