# Market Opportunity Index

Market Opportunity Index is a full-stack educational dashboard for long-term investors. It computes a configurable 0-100 opportunity score for ETFs and stocks such as SPY, QQQ, VTI, NVDA, MSFT, AMZN, GOOGL, META, AMD, SMH, and other AI-related assets.

> **Educational tool only. Not financial advice. Past performance does not guarantee future results.**

## MVP Architecture

- **Backend:** Python FastAPI
- **Frontend:** React + Tailwind + Vite
- **Database:** local SQLite MVP
- **Scheduler:** APScheduler daily refresh job
- **Market data provider:** yfinance behind a provider abstraction
- **Scoring config:** `backend/app/config/scoring_weights.json`

## Features Included

- Create and manage a ticker watchlist.
- Fetch daily market data through yfinance.
- Compute moving averages, 52-week drawdown, 1M/3M/6M/12M returns, volatility, RSI, and available valuation/fundamental fields.
- Import macro context manually through the API.
- Compute a weighted Opportunity Score across valuation, drawdown, trend, macro, risk, fundamentals, and optional sentiment/concentration risk.
- Display a React dashboard with ticker table, score gauge, score chart area, score explanation, and “why now?” positive/negative signals.
- Save email alert rules for score thresholds and 30-day score increases.
- Run a monthly score-threshold backtest against simple DCA with historical features calculated only from data available as of each backtest date.
- Unit tests for score calculation and backtesting logic.

## Repository Layout

```text
backend/app/main.py
backend/app/data_providers/yfinance_provider.py
backend/app/scoring/opportunity_score.py
backend/app/backtesting/backtest.py
backend/app/notifications/email_service.py
frontend/src/pages/Dashboard.tsx
frontend/src/components/ScoreGauge.tsx
frontend/src/components/TickerTable.tsx
frontend/src/components/ScoreExplanation.tsx
```

## Setup

### 1. Environment

```bash
cp .env.example .env
```

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs are available at <http://localhost:8000/docs>.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.


## Deploy on Vercel

This repo is now Vercel-compatible as a single project:

- `frontend/` is built as a Vite static app.
- `api/index.py` exposes the FastAPI `app` as a Vercel Python Function.
- `vercel.json` builds `frontend/dist`, rewrites `/api/*` to the Python function, and falls back all other paths to the SPA `index.html`.

### Vercel setup from GitHub

1. Push this repository to GitHub/GitLab/Bitbucket.
2. In Vercel, create a new project and import the repository.
3. Keep the repository root as the Vercel project root. Do not select `frontend/` as the root, because Vercel also needs `api/index.py` and the Python requirements.
4. Keep **Application Preset = Services**. The committed `vercel.json` defines two services with `experimentalServices`:
   - `frontend`: Vite app mounted at `/` from `frontend/`
   - `backend`: FastAPI app mounted at `/api` from `api/index.py`
5. If Vercel still shows "vercel.json required to deploy projects with multiple services", make sure your latest commit containing `vercel.json` is pushed to GitHub, then click **Refresh** on the import screen.
6. Add environment variables in Vercel Project Settings:
   - `VITE_API_BASE` should be empty or omitted in production so browser calls use same-origin `/api`.
   - `CORS_ORIGINS` can be omitted for same-origin calls, or set to your custom domain for external API callers.
   - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, and `EMAIL_FROM` are only needed if you send real email alerts.
7. Deploy. The frontend will be served from Vercel's CDN and API calls such as `/api/health` will run through the FastAPI service.

### Important Vercel storage note

The MVP still uses SQLite. On Vercel, SQLite is created under `/tmp` so the function can write to it, but this storage is ephemeral and can reset between deployments or cold starts. That is fine for a demo deployment, but production watchlists, score history, macro context, and notification rules should be moved to durable storage such as Vercel Postgres, Neon, Supabase, Turso/libSQL, or another managed database.

### Local Vercel-style development

```bash
npm install -g vercel
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm --prefix frontend install
vercel dev
```

For classic local development without Vercel, continue using `uvicorn app.main:app` in `backend/` and set `VITE_API_BASE=http://localhost:8000` for the frontend. For Vercel Services local development, use `vercel dev -L`.

## Scoring Weights

Edit `backend/app/config/scoring_weights.json` to rebalance the score:

```json
{
  "valuation_attractiveness": 0.18,
  "recent_drawdown": 0.18,
  "long_term_trend_quality": 0.20,
  "macro_conditions": 0.14,
  "volatility_risk": 0.12,
  "earnings_growth_fundamentals": 0.12,
  "sentiment_concentration_risk": 0.06
}
```

Weights are normalized at runtime, so they do not need to sum exactly to 1.

## API Examples

Add a ticker:

```bash
curl -X POST http://localhost:8000/api/watchlist \
  -H 'Content-Type: application/json' \
  -d '{"ticker":"AVGO"}'
```

Import macro context:

```bash
curl -X POST http://localhost:8000/api/macro \
  -H 'Content-Type: application/json' \
  -d '{"treasury_10y":4.4,"inflation":3.1,"fed_funds_rate":5.25,"vix":17,"unemployment_rate":4.0}'
```

Run a backtest:

```bash
curl -X POST http://localhost:8000/api/backtest \
  -H 'Content-Type: application/json' \
  -d '{"ticker":"SPY","threshold":70,"monthly_amount":500}'
```

## Testing

```bash
cd backend
PYTHONPATH=. pytest
```

## Important Limitations

- This MVP uses yfinance, which is convenient for development but should be replaced or supplemented for production reliability.
- Macro data is manually imported in the MVP; production deployments should add explicit FRED/treasury/VIX/breadth providers.
- Email sending requires SMTP configuration. Use a local SMTP catcher such as MailHog for development.
- Scores are educational signals only and should not be treated as investment recommendations.
