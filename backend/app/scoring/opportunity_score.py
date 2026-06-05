"""Opportunity score calculation for educational long-term investing signals."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

DEFAULT_WEIGHTS_PATH = Path(__file__).resolve().parents[1] / "config" / "scoring_weights.json"

DISCLAIMER = (
    "Educational tool only. Not financial advice. Past performance does not "
    "guarantee future results."
)


@dataclass(frozen=True)
class ComponentScore:
    name: str
    score: float
    weight: float
    explanation: str


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def load_weights(path: str | Path = DEFAULT_WEIGHTS_PATH) -> dict[str, float]:
    with Path(path).open("r", encoding="utf-8") as fh:
        weights = {str(k): float(v) for k, v in json.load(fh).items()}
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("Scoring weights must sum to a positive value")
    return {key: value / total for key, value in weights.items()}


def valuation_score(metrics: dict[str, Any]) -> tuple[float, str]:
    pe = _safe_float(metrics.get("pe"))
    forward_pe = _safe_float(metrics.get("forward_pe"))
    ps = _safe_float(metrics.get("price_to_sales"))
    pieces: list[float] = []
    if pe and pe > 0:
        pieces.append(clamp(100 - (pe - 10) * 2.0))
    if forward_pe and forward_pe > 0:
        pieces.append(clamp(100 - (forward_pe - 12) * 2.4))
    if ps and ps > 0:
        pieces.append(clamp(100 - (ps - 2) * 8.0))
    if not pieces:
        return 50.0, "Valuation data unavailable; using neutral valuation score."
    score = sum(pieces) / len(pieces)
    return score, "Lower valuation multiples improve this component; expensive multiples reduce it."


def drawdown_score(metrics: dict[str, Any]) -> tuple[float, str]:
    drawdown = abs(_safe_float(metrics.get("drawdown_52w"), 0.0) or 0.0)
    score = clamp(35 + drawdown * 2.2)
    return score, "Larger 52-week drawdowns can improve opportunity, while extreme weakness is balanced by trend/risk components."


def trend_score(metrics: dict[str, Any]) -> tuple[float, str]:
    price = _safe_float(metrics.get("price"))
    ma50 = _safe_float(metrics.get("ma50"))
    ma100 = _safe_float(metrics.get("ma100"))
    ma200 = _safe_float(metrics.get("ma200"))
    ret12m = _safe_float(metrics.get("return_12m"), 0.0) or 0.0
    score = 45.0 + clamp(ret12m, -40, 60) * 0.45
    if price and ma50 and price > ma50:
        score += 10
    if ma50 and ma100 and ma50 > ma100:
        score += 10
    if ma100 and ma200 and ma100 > ma200:
        score += 10
    if price and ma200 and price < ma200:
        score -= 15
    return clamp(score), "Trend quality rewards positive long-term returns and constructive moving-average alignment."


def macro_score(macro: dict[str, Any]) -> tuple[float, str]:
    score = 55.0
    fed = _safe_float(macro.get("fed_funds_rate"))
    ten_year = _safe_float(macro.get("treasury_10y"))
    inflation = _safe_float(macro.get("inflation"))
    vix = _safe_float(macro.get("vix"))
    unemployment = _safe_float(macro.get("unemployment_rate"))
    breadth = _safe_float(macro.get("market_breadth"))
    if fed is not None:
        score += clamp(5 - fed, -5, 5) * 3
    if ten_year is not None:
        score += clamp(4.5 - ten_year, -4, 4) * 2
    if inflation is not None:
        score += clamp(3 - inflation, -4, 4) * 3
    if vix is not None:
        score += clamp(25 - vix, -15, 15) * 1.1
    if unemployment is not None and unemployment > 6:
        score -= min(15, (unemployment - 6) * 4)
    if breadth is not None:
        score += clamp((breadth - 50) * 0.4, -10, 10)
    return clamp(score), "Macro score uses optional rates, inflation, VIX, unemployment, and breadth inputs; missing fields are neutral."


def volatility_score(metrics: dict[str, Any]) -> tuple[float, str]:
    vol = _safe_float(metrics.get("volatility"), 25.0) or 25.0
    rsi = _safe_float(metrics.get("rsi"), 50.0) or 50.0
    score = clamp(100 - max(0, vol - 10) * 2.2)
    if rsi > 75:
        score -= 12
    elif rsi < 35:
        score += 8
    return clamp(score), "Lower realized volatility helps this component; overbought RSI reduces it and oversold RSI modestly improves it."


def fundamentals_score(metrics: dict[str, Any]) -> tuple[float, str]:
    growth = _safe_float(metrics.get("earnings_growth"))
    if growth is None:
        return 50.0, "Earnings growth unavailable; using neutral fundamentals score."
    # yfinance often returns growth as a decimal, e.g. 0.15 = 15%.
    growth_pct = growth * 100 if abs(growth) <= 3 else growth
    return clamp(50 + growth_pct * 1.4), "Higher earnings growth improves the fundamentals component."


def concentration_score(metrics: dict[str, Any]) -> tuple[float, str]:
    concentration = _safe_float(metrics.get("concentration_risk"), 50.0) or 50.0
    sentiment = _safe_float(metrics.get("sentiment"), 50.0) or 50.0
    score = clamp(50 + (sentiment - 50) * 0.4 - (concentration - 50) * 0.35)
    return score, "Optional sentiment helps, while high concentration risk reduces this small component."


def calculate_opportunity_score(
    metrics: dict[str, Any],
    macro: dict[str, Any] | None = None,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Return a 0-100 opportunity score and explanation without financial advice."""
    macro = macro or {}
    weights = weights or load_weights()
    calculators = {
        "valuation_attractiveness": valuation_score(metrics),
        "recent_drawdown": drawdown_score(metrics),
        "long_term_trend_quality": trend_score(metrics),
        "macro_conditions": macro_score(macro),
        "volatility_risk": volatility_score(metrics),
        "earnings_growth_fundamentals": fundamentals_score(metrics),
        "sentiment_concentration_risk": concentration_score(metrics),
    }
    components = [
        ComponentScore(name=key, score=score, weight=weights.get(key, 0.0), explanation=explanation)
        for key, (score, explanation) in calculators.items()
    ]
    total = clamp(sum(component.score * component.weight for component in components))
    sorted_components = sorted(components, key=lambda c: c.score - 50, reverse=True)
    positives = [c for c in sorted_components if c.score >= 60][:3]
    negatives = [c for c in sorted(components, key=lambda c: c.score) if c.score <= 45][:3]
    return {
        "score": round(total, 1),
        "components": [component.__dict__ for component in components],
        "explanation": "Weighted blend of valuation, drawdown, trend, macro, risk, fundamentals, and optional sentiment signals.",
        "why_now": {
            "positive": [f"{c.name}: {round(c.score, 1)} - {c.explanation}" for c in positives],
            "negative": [f"{c.name}: {round(c.score, 1)} - {c.explanation}" for c in negatives],
        },
        "disclaimer": DISCLAIMER,
    }
