type Props = { score: number; ticker?: string };

export default function ScoreGauge({ score, ticker }: Props) {
  const safeScore = Math.max(0, Math.min(100, score));
  const angle = safeScore * 1.8 - 90;
  const color = safeScore >= 70 ? 'text-emerald-300' : safeScore >= 50 ? 'text-amber-300' : 'text-rose-300';

  return (
    <div className="card flex flex-col items-center gap-4">
      <div className="text-sm uppercase tracking-[0.3em] text-slate-400">Opportunity Score</div>
      <div className="relative h-40 w-80 overflow-hidden">
        <div className="absolute left-0 top-0 h-80 w-80 rounded-full border-[28px] border-slate-700" />
        <div className="absolute left-0 top-0 h-80 w-80 rounded-full border-[28px] border-cyan-400" style={{ clipPath: `inset(${100 - safeScore}% 0 0 0)` }} />
        <div className="absolute bottom-0 left-1/2 h-1 w-32 origin-left rounded bg-white" style={{ transform: `rotate(${angle}deg)` }} />
      </div>
      <div className={`text-6xl font-black ${color}`}>{safeScore.toFixed(1)}</div>
      <div className="text-slate-400">{ticker ? `${ticker} educational signal` : 'Select a ticker'}</div>
    </div>
  );
}
