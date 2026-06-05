"""Backtesting utilities that avoid look-ahead bias."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from math import sqrt
from typing import Any, Callable, Iterable

from app.scoring.opportunity_score import calculate_opportunity_score


@dataclass(frozen=True)
class BacktestResult:
    rows: list[dict[str, Any]]
    strategy_value: float
    dca_value: float
    strategy_shares: float
    dca_shares: float
    cash_invested_strategy: float
    cash_invested_dca: float


def metrics_as_of(history: Any, as_of: Any) -> dict[str, Any]:
    """Build features using only rows at or before the historical date."""
    rows = [row for row in _normalize_history(history) if row["date"] <= _date_key(as_of)]
    if len(rows) < 30:
        raise ValueError("At least 30 historical rows are required before scoring")
    closes = [float(row["close"]) for row in rows]
    latest = closes[-1]
    high_52w = max(closes[-252:])
    returns = [(closes[i] / closes[i - 1] - 1) for i in range(1, len(closes)) if closes[i - 1] != 0]
    return {
        "price": latest,
        "volume": rows[-1].get("volume"),
        "ma50": _ma(closes, 50),
        "ma100": _ma(closes, 100),
        "ma200": _ma(closes, 200),
        "drawdown_52w": (latest / high_52w - 1) * 100 if high_52w else 0,
        "return_1m": _period_return(closes, 21),
        "return_3m": _period_return(closes, 63),
        "return_6m": _period_return(closes, 126),
        "return_12m": _period_return(closes, 252),
        "volatility": _stddev(returns) * sqrt(252) * 100,
        "rsi": _rsi(closes),
    }


def run_monthly_score_backtest(
    history: Any,
    threshold: float = 70,
    monthly_amount: float = 500,
    macro_provider: Callable[[Any], dict[str, Any]] | None = None,
) -> BacktestResult:
    """Invest monthly only when score exceeds threshold and compare with DCA.

    The score for each month is calculated from data available through that date.
    No future rows are used to decide whether to invest.
    """
    rows = _normalize_history(history)
    if not rows:
        raise ValueError("History is required")
    month_end_rows: list[dict[str, Any]] = []
    for row in rows:
        if month_end_rows and row["date"][:7] == month_end_rows[-1]["date"][:7]:
            month_end_rows[-1] = row
        else:
            month_end_rows.append(row)

    strategy_shares = dca_shares = 0.0
    invested_strategy = invested_dca = 0.0
    result_rows: list[dict[str, Any]] = []
    for row in month_end_rows:
        trade_date = row["date"]
        if len([candidate for candidate in rows if candidate["date"] <= trade_date]) < 30:
            continue
        price = float(row["close"])
        metrics = metrics_as_of(rows, trade_date)
        macro = macro_provider(trade_date) if macro_provider else {}
        score = calculate_opportunity_score(metrics, macro)["score"]
        dca_shares += monthly_amount / price
        invested_dca += monthly_amount
        strategy_invested = score >= threshold
        if strategy_invested:
            strategy_shares += monthly_amount / price
            invested_strategy += monthly_amount
        result_rows.append(
            {
                "date": trade_date,
                "price": round(price, 2),
                "score": score,
                "strategy_invested": strategy_invested,
                "strategy_value": round(strategy_shares * price, 2),
                "dca_value": round(dca_shares * price, 2),
            }
        )
    final_price = float(rows[-1]["close"])
    return BacktestResult(
        rows=result_rows,
        strategy_value=round(strategy_shares * final_price, 2),
        dca_value=round(dca_shares * final_price, 2),
        strategy_shares=strategy_shares,
        dca_shares=dca_shares,
        cash_invested_strategy=invested_strategy,
        cash_invested_dca=invested_dca,
    )


def _normalize_history(history: Any) -> list[dict[str, Any]]:
    if isinstance(history, list):
        return sorted(
            [
                {
                    "date": _date_key(row.get("date")),
                    "close": row.get("close", row.get("Close")),
                    "volume": row.get("volume", row.get("Volume")),
                }
                for row in history
            ],
            key=lambda row: row["date"],
        )
    if hasattr(history, "sort_index") and hasattr(history, "iterrows"):
        frame = history.sort_index()
        normalized = []
        for index, row in frame.iterrows():
            normalized.append(
                {
                    "date": _date_key(index),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]) if "Volume" in row and row["Volume"] == row["Volume"] else None,
                }
            )
        return normalized
    raise TypeError("history must be a list of rows or a pandas-like DataFrame")


def _date_key(value: Any) -> str:
    if isinstance(value, str):
        return value[:10]
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "date"):
        return value.date().isoformat()
    return str(value)[:10]


def _ma(closes: list[float], window: int) -> float | None:
    if len(closes) < window:
        return None
    return sum(closes[-window:]) / window


def _period_return(closes: list[float], periods: int) -> float | None:
    if len(closes) <= periods or closes[-periods] == 0:
        return None
    return (closes[-1] / closes[-periods] - 1) * 100


def _stddev(values: Iterable[float]) -> float:
    values = list(values)
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return variance ** 0.5


def _rsi(closes: list[float], window: int = 14) -> float | None:
    if len(closes) <= window:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    recent = deltas[-window:]
    gains = [max(delta, 0) for delta in recent]
    losses = [abs(min(delta, 0)) for delta in recent]
    avg_gain = sum(gains) / window
    avg_loss = sum(losses) / window
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
