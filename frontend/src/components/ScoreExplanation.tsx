type Component = { name: string; score: number; weight: number; explanation: string };
type Props = {
  explanation?: string;
  components?: Component[];
  whyNow?: { positive: string[]; negative: string[] };
};

export default function ScoreExplanation({ explanation, components = [], whyNow }: Props) {
  return (
    <div className="card space-y-5">
      <div>
        <h2 className="text-xl font-bold">Score Explanation</h2>
        <p className="mt-2 text-slate-300">{explanation ?? 'Fetch a ticker to see the weighted opportunity components.'}</p>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {components.map((component) => (
          <div key={component.name} className="rounded-xl bg-slate-950 p-3">
            <div className="flex justify-between gap-4">
              <span className="font-semibold capitalize">{component.name.replace(/_/g, ' ')}</span>
              <span>{component.score.toFixed(1)} · {(component.weight * 100).toFixed(0)}%</span>
            </div>
            <p className="mt-1 text-sm text-slate-400">{component.explanation}</p>
          </div>
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <SignalList title="Strongest positive signals" items={whyNow?.positive ?? []} tone="positive" />
        <SignalList title="Strongest negative signals" items={whyNow?.negative ?? []} tone="negative" />
      </div>
    </div>
  );
}

function SignalList({ title, items, tone }: { title: string; items: string[]; tone: 'positive' | 'negative' }) {
  const color = tone === 'positive' ? 'text-emerald-300' : 'text-rose-300';
  return (
    <div>
      <h3 className={`font-bold ${color}`}>{title}</h3>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-300">
        {(items.length ? items : ['No standout signal yet.']).map((item) => <li key={item}>{item}</li>)}
      </ul>
    </div>
  );
}
