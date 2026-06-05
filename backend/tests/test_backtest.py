from datetime import date, timedelta

from app.backtesting.backtest import metrics_as_of, run_monthly_score_backtest


def make_history(days=420):
    start = date(2023, 1, 2)
    rows = []
    current = start
    while len(rows) < days:
        if current.weekday() < 5:
            rows.append({"date": current.isoformat(), "close": 100 + len(rows) * 0.15, "volume": 1_000_000})
        current += timedelta(days=1)
    return rows


def test_metrics_as_of_uses_only_past_rows():
    history = make_history()
    as_of = history[120]["date"]

    metrics = metrics_as_of(history, as_of)

    assert metrics["price"] == history[120]["close"]
    assert metrics["price"] != history[-1]["close"]


def test_monthly_backtest_compares_strategy_to_dca():
    history = make_history()

    result = run_monthly_score_backtest(history, threshold=0, monthly_amount=100)

    assert result.rows
    assert result.cash_invested_strategy == result.cash_invested_dca
    assert result.strategy_value == result.dca_value
