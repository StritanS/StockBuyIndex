export type ScoreItem = {
  ticker: string;
  metrics?: Record<string, number | string | null>;
  score?: { score: number };
  error?: string;
};

type Props = { items: ScoreItem[]; selected?: string; onSelect: (ticker: string) => void };

export default function TickerTable({ items, selected, onSelect }: Props) {
  return (
    <div className="card overflow-x-auto">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-bold">Ticker Table</h2>
        <span className="text-sm text-slate-400">Scores are educational only</span>
      </div>
      <table className="w-full text-left text-sm">
        <thead className="text-slate-400">
          <tr>
            <th className="py-2">Ticker</th>
            <th>Score</th>
            <th>Price</th>
            <th>52W Drawdown</th>
            <th>12M Return</th>
            <th>RSI</th>
            <th>Volatility</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.ticker}
              onClick={() => onSelect(item.ticker)}
              className={`cursor-pointer border-t border-slate-800 hover:bg-slate-800/70 ${selected === item.ticker ? 'bg-slate-800' : ''}`}
            >
              <td className="py-3 font-bold text-cyan-300">{item.ticker}</td>
              {item.error ? (
                <td colSpan={6} className="text-rose-300">{item.error}</td>
              ) : (
                <>
                  <td>{item.score?.score?.toFixed(1) ?? '—'}</td>
                  <td>{fmt(item.metrics?.price)}</td>
                  <td>{fmt(item.metrics?.drawdown_52w)}%</td>
                  <td>{fmt(item.metrics?.return_12m)}%</td>
                  <td>{fmt(item.metrics?.rsi)}</td>
                  <td>{fmt(item.metrics?.volatility)}%</td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function fmt(value: unknown) {
  return typeof value === 'number' ? value.toFixed(1) : '—';
}
