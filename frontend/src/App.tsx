import { useEffect, useState } from "react";

type Scenario = {
  id: string;
  title: string;
  description: string;
  expected_outcome: string;
};

type TraceEntry = {
  type: string;
  text: string;
  badge?: string;
};

const API_BASE = "/api";

const fallbackScenarios: Scenario[] = [
  { id: "S1-A", title: "Accept", description: "Healthy demand with valid coverage and budget.", expected_outcome: "Accept" },
  { id: "S1-B", title: "Modify over-order", description: "Open POs cover part of demand; reorder should be reduced.", expected_outcome: "Modify" },
  { id: "S1-C", title: "Modify storage", description: "Need exceeds storage; split or postpone.", expected_outcome: "Modify" },
  { id: "S1-D", title: "Modify budget", description: "Budget cap requires lower quantity.", expected_outcome: "Modify" },
  { id: "S1-E", title: "Reject", description: "Incoming stock already covers the horizon.", expected_outcome: "Reject" },
  { id: "S1-F", title: "Investigate", description: "Forecast stale or low-accuracy; backfill with history.", expected_outcome: "Investigate_Further" },
];

const defaultKpis = [
  { label: "Auto-decisions", value: "--", delta: "live", tone: "emerald" },
  { label: "POs created", value: "--", delta: "live", tone: "cyan" },
  { label: "Avoided stockouts", value: "--", delta: "live", tone: "violet" },
  { label: "Escalations", value: "--", delta: "live", tone: "amber" },
];

function formatStepText(step: Record<string, any>): string {
  if (step.type === "decision") {
    const payload = step.payload ?? {};
    const decision = payload.decision ?? payload.final_decision ?? "Decision";
    const qty = payload.quantity ?? payload.recommended_qty ?? payload.qty ?? "";
    const supplier = payload.supplier_id ?? "";
    return `Decision: ${decision}${qty ? ` | qty ${qty}` : ""}${supplier ? ` | supplier ${supplier}` : ""}`;
  }

  if (step.type === "validation") {
    const payload = step.payload ?? {};
    const allowed = payload.allowed ?? payload.valid ?? payload.status ?? "validation";
    return `Validation: ${allowed}`;
  }

  if (step.type === "observation") {
    const payload = step.payload ?? {};
    if (typeof payload === "string") return payload;
    if (payload && typeof payload === "object") {
      const summary = Object.entries(payload)
        .slice(0, 3)
        .map(([key, value]) => `${key}=${String(value)}`)
        .join(" | ");
      return summary || "Observation recorded";
    }
    return "Observation recorded";
  }

  return `Trace: ${JSON.stringify(step.payload ?? {})}`;
}

export default function App() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState("S1-A");
  const [decision, setDecision] = useState("--");
  const [trace, setTrace] = useState<TraceEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/scenarios`)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        const nextScenarios = Array.isArray(data) && data.length > 0 ? data : fallbackScenarios;
        setScenarios(nextScenarios);
        setSelectedScenarioId(nextScenarios[0]?.id ?? "S1-A");
      })
      .catch(() => {
        setScenarios(fallbackScenarios);
        setSelectedScenarioId("S1-A");
        setError("Backend not reachable; showing a local fallback scenario list.");
      });
  }, []);

  const resetRunState = () => {
    setRunId(null);
    setDecision("--");
    setTrace([]);
    setError(null);
  };

  const handleRunAgent = async () => {
    const payload = {
      scenario_id: selectedScenarioId,
      recommended_qty: 800,
      supplier_id: "SUP-1",
      node_id: "NODE-1",
    };

    resetRunState();
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/agent/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Agent request failed with status ${response.status}`);
      }

      const result = await response.json();
      const nextRunId = result.run_id ?? null;
      setRunId(nextRunId);
      setDecision(result.final_decision ?? "--");

      const nextTrace = (result.steps ?? []).map((step: Record<string, any>, index: number) => {
        const text = formatStepText(step);
        const badge = step.type === "observation" ? "read" : step.type === "validation" ? "check" : step.type === "decision" ? "decision" : "trace";
        return { type: step.type ?? `step-${index + 1}`, text, badge };
      });

      setTrace(nextTrace.length > 0 ? nextTrace : [{ type: "system", text: "Agent run completed but no trace steps were returned." }]);

      if (nextRunId) {
        const stream = new EventSource(`${API_BASE}/agent/runs/${nextRunId}/stream`);
        stream.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.event === "run") {
            setDecision(data.final_decision ?? "--");
            return;
          }
          if (data.event === "step") {
            const item = {
              type: data.type ?? "step",
              text: formatStepText({ type: data.type, payload: data.payload }),
              badge: data.type === "observation" ? "read" : data.type === "validation" ? "check" : data.type === "decision" ? "decision" : "trace",
            };
            setTrace((current) => [...current, item]);
          }
          if (data.event === "done") {
            stream.close();
          }
        };
        stream.onerror = () => {
          stream.close();
        };
      }
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Agent run failed.");
      setDecision("ERROR");
      setTrace([{ type: "error", text: "The live agent call failed. Check that the backend is running on port 8000." }]);
    } finally {
      setLoading(false);
    }
  };

  const selectedScenario = scenarios.find((scenario) => scenario.id === selectedScenarioId) ?? scenarios[0];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-violet-950 px-4 py-6 text-slate-50">
      <div className="mx-auto max-w-7xl">
        <header className="mb-6 flex flex-col gap-4 rounded-3xl border border-white/10 bg-white/5 p-5 shadow-2xl backdrop-blur-xl md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-cyan-300">AI purchasing agent</p>
            <h1 className="mt-2 text-3xl font-black tracking-tight text-white">Retail Supply Orchestration</h1>
          </div>
          <div className="flex items-center gap-3">
            <button className="rounded-full border border-cyan-400/40 bg-cyan-500/10 px-4 py-2 text-sm font-semibold text-cyan-200">Live</button>
            <button
              onClick={handleRunAgent}
              disabled={loading}
              className="rounded-full bg-gradient-to-r from-coral to-violet-500 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-violet-900/30 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Running..." : "Run Agent"}
            </button>
          </div>
        </header>

        {error ? (
          <div className="mb-6 rounded-2xl border border-red-500/35 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>
        ) : null}

        <section className="mb-6 grid gap-4 md:grid-cols-4">
          {defaultKpis.map((item, index) => (
            <article key={item.label} className="rounded-2xl border border-white/10 bg-white/5 p-4 shadow-lg">
              <p className="text-sm text-slate-300">{item.label}</p>
              <div className="mt-3 flex items-end justify-between">
                <span className="text-3xl font-black tabular-nums text-white">
                  {index === 0 && decision !== "--" ? `${decision}` : item.value}
                </span>
                <span className="rounded-full bg-emerald-500/10 px-2 py-1 text-xs font-semibold text-emerald-300">{item.delta}</span>
              </div>
            </article>
          ))}
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-3xl border border-white/10 bg-slate-900/60 p-5 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-bold text-white">Scenario runner</h2>
              <span className="rounded-full border border-violet-400/30 bg-violet-500/10 px-2 py-1 text-xs font-medium text-violet-200">{scenarios.length} scenario families</span>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {scenarios.map((scenario) => (
                <button
                  key={scenario.id}
                  onClick={() => {
                    setSelectedScenarioId(scenario.id);
                    resetRunState();
                  }}
                  className={`rounded-2xl border p-4 text-left transition hover:-translate-y-0.5 ${selectedScenarioId === scenario.id ? "border-cyan-400/80 bg-cyan-500/10" : "border-white/10 bg-gradient-to-br from-slate-800 to-slate-900 hover:border-cyan-400/50"}`}
                >
                  <div className="mb-3 flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">{scenario.id}</span>
                    <span className="rounded-full bg-emerald-500/10 px-2 py-1 text-[10px] font-bold text-emerald-300">{scenario.expected_outcome}</span>
                  </div>
                  <h3 className="text-base font-semibold text-white">{scenario.title}</h3>
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-3xl border border-white/10 bg-slate-900/60 p-5 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-bold text-white">Decision card</h2>
              <span className="rounded-full bg-amber-500/10 px-2 py-1 text-xs font-medium text-amber-200">{decision}</span>
            </div>
            <div className="space-y-4">
              <div className="rounded-2xl bg-slate-800/80 p-4">
                <div className="flex items-center justify-between text-sm text-slate-300">
                  <span>Scenario</span>
                  <span className="text-lg font-black text-white">{selectedScenario?.id ?? "--"}</span>
                </div>
                <div className="mt-2 flex items-center justify-between text-sm text-slate-300">
                  <span>Run ID</span>
                  <span className="text-sm font-black text-amber-300">{runId ?? "not started"}</span>
                </div>
              </div>
              <div className="space-y-2 text-sm text-slate-300">
                <div className="flex items-center justify-between"><span>Title</span><span>{selectedScenario?.title ?? "--"}</span></div>
                <div className="flex items-center justify-between"><span>Node</span><span>NODE-1</span></div>
                <div className="flex items-center justify-between"><span>Supplier</span><span>SUP-1</span></div>
                <div className="flex items-center justify-between"><span>Status</span><span>{loading ? "running" : decision}</span></div>
              </div>
            </div>
          </div>
        </section>

        <section className="mt-6 grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-3xl border border-white/10 bg-slate-900/60 p-5 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-bold text-white">Live agent trace</h2>
              <span className="text-sm text-cyan-300">{trace.length} events</span>
            </div>
            <div className="space-y-3">
              {trace.map((item, index) => (
                <div key={`${item.type}-${index}`} className="rounded-2xl border border-white/10 bg-slate-800/80 p-3">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">{item.type}</span>
                    {item.badge ? <span className="rounded-full bg-violet-500/10 px-2 py-1 text-[10px] font-bold text-violet-200">{item.badge}</span> : null}
                  </div>
                  <p className="text-sm text-slate-200">{item.text}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-3xl border border-white/10 bg-slate-900/60 p-5 shadow-xl">
            <h2 className="text-xl font-bold text-white">Constraint visualizer</h2>
            <div className="mt-5 space-y-4">
              {[
                ["Budget", decision === "MODIFY" ? 72 : 48, "bg-gradient-to-r from-emerald-400 to-cyan-400"],
                ["Storage", decision === "REJECT" ? 25 : 61, "bg-gradient-to-r from-violet-400 to-indigo-400"],
                ["Lead-time cover", decision === "INVESTIGATE_FURTHER" ? 54 : 82, "bg-gradient-to-r from-amber-400 to-orange-400"],
              ].map(([label, amount, color]) => (
                <div key={String(label)}>
                  <div className="mb-1 flex justify-between text-sm text-slate-300"><span>{label}</span><span>{amount}%</span></div>
                  <div className="h-2.5 rounded-full bg-slate-800">
                    <div className={`${color} h-2.5 rounded-full`} style={{ width: `${amount}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
