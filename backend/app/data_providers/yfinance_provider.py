"""Data-provider abstraction backed by yfinance for the local MVP."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import yfinance as yf


@dataclass
class MarketSnapshot:
    ticker: str
    metrics: dict[str, Any]
    history: list[dict[str, Any]]


class YFinanceProvider:
    """Fetch market data while keeping API-specific details isolated."""

    def get_ticker_snapshot(self, ticker: str, period: str = "2y") -> MarketSnapshot:
        symbol = ticker.upper().strip()
        yf_ticker = yf.Ticker(symbol)
        history = yf_ticker.history(period=period, auto_adjust=True)
        if history.empty:
            raise ValueError(f"No yfinance history returned for {symbol}")
        metrics = self._metrics_from_history(history, yf_ticker.info or {})
        rows = self._history_rows(history)
        return MarketSnapshot(ticker=symbol, metrics=metrics, history=rows)

    def _metrics_from_history(self, history: pd.DataFrame, info: dict[str, Any]) -> dict[str, Any]:
        close = history["Close"]
        returns = close.pct_change()
        latest = close.iloc[-1]
        high_52w = close.tail(252).max()
        metrics = {
            "price": round(float(latest), 2),
            "volume": int(history["Volume"].iloc[-1]) if "Volume" in history else None,
            "ma50": self._last_ma(close, 50),
            "ma100": self._last_ma(close, 100),
            "ma200": self._last_ma(close, 200),
            "drawdown_52w": round((float(latest) / float(high_52w) - 1) * 100, 2) if high_52w else 0,
            "return_1m": self._period_return(close, 21),
            "return_3m": self._period_return(close, 63),
            "return_6m": self._period_return(close, 126),
            "return_12m": self._period_return(close, 252),
            "volatility": round(float(returns.std() * (252 ** 0.5) * 100), 2),
            "rsi": self._rsi(close),
            "pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "earnings_growth": info.get("earningsGrowth"),
            "concentration_risk": info.get("heldPercentInstitutions"),
        }
        return metrics

    def _history_rows(self, history: pd.DataFrame) -> list[dict[str, Any]]:
        enriched = history.copy()
        enriched["ma50"] = enriched["Close"].rolling(50).mean()
        enriched["ma100"] = enriched["Close"].rolling(100).mean()
        enriched["ma200"] = enriched["Close"].rolling(200).mean()
        output = []
        for index, row in enriched.tail(260).iterrows():
            output.append(
                {
                    "date": index.date().isoformat(),
                    "close": round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]) if not pd.isna(row.get("Volume")) else None,
                    "ma50": None if pd.isna(row["ma50"]) else round(float(row["ma50"]), 2),
                    "ma100": None if pd.isna(row["ma100"]) else round(float(row["ma100"]), 2),
                    "ma200": None if pd.isna(row["ma200"]) else round(float(row["ma200"]), 2),
                }
            )
        return output

    @staticmethod
    def _last_ma(close: pd.Series, window: int) -> float | None:
        value = close.rolling(window).mean().iloc[-1]
        return None if pd.isna(value) else round(float(value), 2)

    @staticmethod
    def _period_return(close: pd.Series, periods: int) -> float | None:
        if len(close) <= periods:
            return None
        return round((float(close.iloc[-1]) / float(close.iloc[-periods]) - 1) * 100, 2)

    @staticmethod
    def _rsi(close: pd.Series, window: int = 14) -> float | None:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(window).mean()
        loss = -delta.clip(upper=0).rolling(window).mean()
        rs = gain / loss.replace(0, pd.NA)
        rsi = 100 - (100 / (1 + rs))
        value = rsi.iloc[-1]
        return None if pd.isna(value) else round(float(value), 2)
