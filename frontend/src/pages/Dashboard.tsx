import { useEffect, useMemo, useState } from 'react';
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import ScoreExplanation from '../components/ScoreExplanation';
import ScoreGauge from '../components/ScoreGauge';
import TickerTable, { ScoreItem } from '../components/TickerTable';
import { apiGet, apiPost } from '../lib/api';

type Detail = {
  ticker: string;
  metrics: Record<string, number | string | null>;
  history: { date: string; close: number; ma50?: number; ma100?: number; ma200?: number }[];
  score: {
    score: number;
    explanation: string;
    components: { name: string; score: number; weight: number; explanation: string }[];
    why_now: { positive: string[]; negative: string[] };
    disclaimer: string;
  };
};

export default function Dashboard() {
  const [items, setItems] = useState<ScoreItem[]>([]);
  const [selected, setSelected] = useState('SPY');
  const [detail, setDetail] = useState<Detail | null>(null);
  const [newTicker, setNewTicker] = useState('');
  const [threshold, setThreshold] = useState(70);
  const [email, setEmail] = useState('');
  const [backtest, setBacktest] = useState<Record<string, unknown> | null>(null);
  const [scoreHistory, setScoreHistory] = useState<{ as_of: string; score: number }[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshScores() {
    setError(null);
    try {
      const data = await apiGet<{ items: ScoreItem[] }>('/api/scores');
      setItems(data.items);
      if (!selected && data.items[0]) setSelected(data.items[0].ticker);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load scores');
    }
  }

  async function loadDetail(ticker: string) {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<Detail>(`/api/tickers/${ticker}`);
      const historyData = await apiGet<{ history: { as_of: string; score: number }[] }>(`/api/scores/${ticker}/history`);
      setDetail(data);
      setScoreHistory(historyData.history);
      setSelected(data.ticker);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load ticker detail');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { refreshScores(); }, []);
  useEffect(() => { if (selected) loadDetail(selected); }, [selected]);

  const selectedScore = detail?.score.score ?? items.find((item) => item.ticker === selected)?.score?.score ?? 0;
  const scoreChart = useMemo(() => {
    if (scoreHistory.length > 0) {
      return scoreHistory.map((row) => ({ date: row.as_of, score: row.score }));
    }
    return detail ? [{ date: 'current', score: selectedScore }] : [];
  }, [detail, scoreHistory, selectedScore]);

  async function addTicker() {
    if (!newTicker.trim()) return;
    setError(null);
    try {
      await apiPost('/api/watchlist', { ticker: newTicker.trim().toUpperCase() });
      setNewTicker('');
      await refreshScores();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to add ticker');
    }
  }

  async function saveNotification() {
    setError(null);
    try {
      await apiPost('/api/notifications', { ticker: selected, email, threshold, increase_points: 15, lookback_days: 30 });
      setEmail('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save notification');
    }
  }

  async function runBacktest() {
    setError(null);
    try {
      const data = await apiPost<Record<string, unknown>>('/api/backtest', { ticker: selected, threshold, monthly_amount: 500 });
      setBacktest(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to run backtest');
    }
  }

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-8">
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.4em] text-cyan-300">Educational tool only</p>
          <h1 className="mt-2 text-4xl font-black md:text-6xl">Market Opportunity Index</h1>
          <p className="mt-3 max-w-3xl text-slate-300">Long-term investing dashboard for watchlists, market data, macro context, score explanations, notifications, and monthly-investing backtests.</p>
        </div>
        <div className="rounded-xl border border-amber-400/50 bg-amber-400/10 p-4 text-sm text-amber-100">
          Not financial advice. Past performance does not guarantee future results.
        </div>
      </header>

      {error && <div className="rounded-xl border border-rose-400 bg-rose-950 p-4 text-rose-100">{error}</div>}

      <section className="grid gap-4 md:grid-cols-[1fr_auto]">
        <div className="card flex flex-wrap gap-3">
          <input className="input" placeholder="Add ticker (e.g. AVGO)" value={newTicker} onChange={(event) => setNewTicker(event.target.value)} />
          <button className="button" onClick={addTicker}>Add to watchlist</button>
          <button className="rounded-lg bg-slate-700 px-4 py-2 font-semibold hover:bg-slate-600" onClick={refreshScores}>Refresh scores</button>
          {loading && <span className="self-center text-slate-400">Loading yfinance data…</span>}
        </div>
        <div className="card flex items-center gap-3">
          <label className="text-sm text-slate-400">Alert threshold</label>
          <input className="input w-24" type="number" value={threshold} onChange={(event) => setThreshold(Number(event.target.value))} />
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <TickerTable items={items} selected={selected} onSelect={setSelected} />
        <ScoreGauge score={selectedScore} ticker={selected} />
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="card h-96">
          <h2 className="mb-4 text-xl font-bold">Historical Score Chart</h2>
          <ResponsiveContainer width="100%" height="85%">
            <LineChart data={scoreChart}>
              <XAxis dataKey="date" hide />
              <YAxis domain={[0, 100]} />
              <Tooltip contentStyle={{ background: '#020617', border: '1px solid #334155' }} />
              <Line type="monotone" dataKey="score" stroke="#22d3ee" dot name="Opportunity score" />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="card space-y-4">
          <h2 className="text-xl font-bold">Notifications & Backtesting</h2>
          <div className="space-y-2">
            <input className="input w-full" placeholder="Email for threshold alert" value={email} onChange={(event) => setEmail(event.target.value)} />
            <button className="button" disabled={!email} onClick={saveNotification}>Save email alert</button>
            <p className="text-sm text-slate-400">Example rules: score &gt; {threshold}, or score rises by more than 15 points in 30 days.</p>
          </div>
          <div className="border-t border-slate-700 pt-4">
            <button className="button" onClick={runBacktest}>Run monthly score backtest</button>
            {backtest && <pre className="mt-3 max-h-48 overflow-auto rounded-lg bg-slate-950 p-3 text-xs">{JSON.stringify(backtest, null, 2)}</pre>}
          </div>
        </div>
      </section>

      <ScoreExplanation explanation={detail?.score.explanation} components={detail?.score.components} whyNow={detail?.score.why_now} />
    </main>
  );
}
