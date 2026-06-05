"""FastAPI entrypoint for the Market Opportunity Index MVP."""
from __future__ import annotations

from datetime import datetime
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.backtesting.backtest import run_monthly_score_backtest
from app.data_providers.yfinance_provider import YFinanceProvider
from app.notifications.email_service import AlertRule, should_notify
from app.scoring.opportunity_score import DISCLAIMER, calculate_opportunity_score

IS_VERCEL = bool(os.getenv("VERCEL"))
DEFAULT_SQLITE_URL = "sqlite:////tmp/market_opportunity.db" if IS_VERCEL else "sqlite:///./market_opportunity.db"
DB_PATH = Path(os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL).replace("sqlite:///", ""))
DEFAULT_TICKERS = ["SPY", "QQQ", "VTI", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "AMD", "SMH"]

app = FastAPI(title="Market Opportunity Index", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
provider = YFinanceProvider()
scheduler = BackgroundScheduler()


class WatchlistRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=12)


class MacroRequest(BaseModel):
    sp500_valuation: float | None = None
    treasury_10y: float | None = None
    inflation: float | None = None
    fed_funds_rate: float | None = None
    vix: float | None = None
    unemployment_rate: float | None = None
    market_breadth: float | None = None


class NotificationRuleRequest(BaseModel):
    ticker: str
    email: str
    threshold: float = 70
    increase_points: float = 15
    lookback_days: int = 30


class BacktestRequest(BaseModel):
    ticker: str
    threshold: float = 70
    monthly_amount: float = 500


def db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS watchlist (ticker TEXT PRIMARY KEY)")
        conn.execute("CREATE TABLE IF NOT EXISTS macro_context (id INTEGER PRIMARY KEY CHECK (id = 1), payload TEXT NOT NULL)")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS score_history (
                ticker TEXT NOT NULL,
                as_of TEXT NOT NULL,
                score REAL NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (ticker, as_of)
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS notification_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                email TEXT NOT NULL,
                threshold REAL NOT NULL,
                increase_points REAL NOT NULL,
                lookback_days INTEGER NOT NULL
            )"""
        )
        for ticker in DEFAULT_TICKERS:
            conn.execute("INSERT OR IGNORE INTO watchlist (ticker) VALUES (?)", (ticker,))


def get_macro_context() -> dict[str, Any]:
    with db() as conn:
        row = conn.execute("SELECT payload FROM macro_context WHERE id = 1").fetchone()
    return json.loads(row["payload"]) if row else {}


def save_score(ticker: str, score_payload: dict[str, Any]) -> None:
    with db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO score_history (ticker, as_of, score, payload) VALUES (?, ?, ?, ?)",
            (ticker, datetime.utcnow().date().isoformat(), score_payload["score"], json.dumps(score_payload)),
        )


def build_ticker_payload(ticker: str) -> dict[str, Any]:
    snapshot = provider.get_ticker_snapshot(ticker)
    score_payload = calculate_opportunity_score(snapshot.metrics, get_macro_context())
    payload = {
        "ticker": snapshot.ticker,
        "metrics": snapshot.metrics,
        "history": snapshot.history,
        "score": score_payload,
        "disclaimer": DISCLAIMER,
    }
    save_score(snapshot.ticker, score_payload)
    return payload


def refresh_watchlist_scores() -> None:
    with db() as conn:
        tickers = [row["ticker"] for row in conn.execute("SELECT ticker FROM watchlist")]
    for ticker in tickers:
        try:
            build_ticker_payload(ticker)
        except Exception as exc:  # scheduled job must not stop on one provider failure
            print(f"Score refresh failed for {ticker}: {exc}")


@app.on_event("startup")
def startup() -> None:
    init_db()
    if not IS_VERCEL:
        scheduler.add_job(refresh_watchlist_scores, "interval", hours=24, id="daily-score-refresh", replace_existing=True)
        scheduler.start()


@app.on_event("shutdown")
def shutdown() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "storage": "ephemeral-sqlite" if IS_VERCEL else "sqlite", "disclaimer": DISCLAIMER}


@app.get("/api/watchlist")
def get_watchlist() -> dict[str, Any]:
    with db() as conn:
        tickers = [row["ticker"] for row in conn.execute("SELECT ticker FROM watchlist ORDER BY ticker")]
    return {"tickers": tickers, "disclaimer": DISCLAIMER}


@app.post("/api/watchlist")
def add_ticker(request: WatchlistRequest) -> dict[str, Any]:
    ticker = request.ticker.upper().strip()
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO watchlist (ticker) VALUES (?)", (ticker,))
    return {"ticker": ticker, "message": "Added to watchlist", "disclaimer": DISCLAIMER}


@app.delete("/api/watchlist/{ticker}")
def delete_ticker(ticker: str) -> dict[str, Any]:
    with db() as conn:
        conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker.upper(),))
    return {"ticker": ticker.upper(), "message": "Removed from watchlist"}


@app.get("/api/tickers/{ticker}")
def ticker_detail(ticker: str) -> dict[str, Any]:
    try:
        return build_ticker_payload(ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/scores")
def scores() -> dict[str, Any]:
    with db() as conn:
        tickers = [row["ticker"] for row in conn.execute("SELECT ticker FROM watchlist ORDER BY ticker")]
    items = []
    for ticker in tickers:
        try:
            item = build_ticker_payload(ticker)
            items.append({"ticker": ticker, "metrics": item["metrics"], "score": item["score"]})
        except Exception as exc:
            items.append({"ticker": ticker, "error": str(exc)})
    return {"items": items, "disclaimer": DISCLAIMER}


@app.post("/api/macro")
def set_macro_context(request: MacroRequest) -> dict[str, Any]:
    payload = request.model_dump(exclude_none=True)
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO macro_context (id, payload) VALUES (1, ?)", (json.dumps(payload),))
    return {"macro": payload, "message": "Macro context saved"}


@app.get("/api/scores/{ticker}/history")
def score_history(ticker: str) -> dict[str, Any]:
    with db() as conn:
        rows = conn.execute(
            "SELECT as_of, score, payload FROM score_history WHERE ticker = ? ORDER BY as_of",
            (ticker.upper(),),
        ).fetchall()
    return {"ticker": ticker.upper(), "history": [dict(row) for row in rows]}


@app.post("/api/notifications")
def create_notification_rule(request: NotificationRuleRequest) -> dict[str, Any]:
    with db() as conn:
        conn.execute(
            "INSERT INTO notification_rules (ticker, email, threshold, increase_points, lookback_days) VALUES (?, ?, ?, ?, ?)",
            (request.ticker.upper(), request.email, request.threshold, request.increase_points, request.lookback_days),
        )
    rule = AlertRule(request.ticker.upper(), request.threshold, request.increase_points, request.lookback_days)
    return {"rule": rule.__dict__, "email": request.email, "message": "Notification rule saved"}


@app.post("/api/notifications/evaluate")
def evaluate_notification(rule: NotificationRuleRequest, current_score: float, previous_score: float | None = None) -> dict[str, Any]:
    matched, reason = should_notify(current_score, previous_score, AlertRule(rule.ticker.upper(), rule.threshold, rule.increase_points, rule.lookback_days))
    return {"notify": matched, "reason": reason}


@app.post("/api/backtest")
def backtest(request: BacktestRequest) -> dict[str, Any]:
    snapshot = provider.get_ticker_snapshot(request.ticker, period="10y")
    import yfinance as yf

    history = yf.Ticker(request.ticker.upper()).history(period="10y", auto_adjust=True)
    if history.empty:
        raise HTTPException(status_code=404, detail="No history for backtest")
    result = run_monthly_score_backtest(history, request.threshold, request.monthly_amount)
    return {"ticker": snapshot.ticker, "result": result.__dict__, "disclaimer": DISCLAIMER}
