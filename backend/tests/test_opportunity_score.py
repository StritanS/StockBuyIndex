from app.scoring.opportunity_score import calculate_opportunity_score, load_weights


def test_score_is_bounded_and_contains_disclaimer():
    metrics = {
        "price": 110,
        "ma50": 105,
        "ma100": 100,
        "ma200": 90,
        "drawdown_52w": -18,
        "return_12m": 24,
        "volatility": 22,
        "rsi": 42,
        "pe": 24,
        "forward_pe": 20,
        "price_to_sales": 6,
        "earnings_growth": 0.18,
    }
    macro = {"fed_funds_rate": 4.5, "inflation": 3.2, "vix": 18, "unemployment_rate": 4.1}

    result = calculate_opportunity_score(metrics, macro)

    assert 0 <= result["score"] <= 100
    assert result["components"]
    assert "Not financial advice" in result["disclaimer"]
    assert "why_now" in result


def test_weights_are_normalized():
    weights = load_weights()
    assert round(sum(weights.values()), 6) == 1
