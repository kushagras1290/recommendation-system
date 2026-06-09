"use client";

import { useEffect, useState } from "react";
import { fetchExperiments, createExperiment } from "@/lib/api";
import type { ExperimentResult, VariantResult } from "@/lib/types";

const MODELS = ["popularity", "content_based", "collaborative_filtering", "ranker"];
const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  running: { bg: "#1d4f35", text: "#4ade80" },
  draft: { bg: "#1e293b", text: "#94a3b8" },
  completed: { bg: "#1e3a5f", text: "#93c5fd" },
};

function LiftBadge({ lift }: { lift: number }) {
  const isPos = lift > 0;
  return (
    <span
      style={{
        fontSize: "0.75rem",
        padding: "2px 8px",
        borderRadius: 9999,
        backgroundColor: isPos ? "#1d4f35" : (lift < 0 ? "#3b1f1f" : "#1e293b"),
        color: isPos ? "#4ade80" : (lift < 0 ? "#f87171" : "#94a3b8"),
        fontWeight: 600,
      }}
    >
      {isPos ? "+" : ""}{lift.toFixed(1)}% lift
    </span>
  );
}

function ExperimentCard({ exp }: { exp: ExperimentResult }) {
  const statusStyle = STATUS_COLORS[exp.status] || STATUS_COLORS.draft;

  return (
    <div className="card" style={{ padding: "1.25rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
        <div>
          <h3 style={{ fontWeight: 600, color: "#f1f5f9", fontSize: "0.95rem" }}>{exp.name}</h3>
          <div style={{ display: "flex", gap: 8, marginTop: 4, alignItems: "center" }}>
            <span
              style={{
                fontSize: "0.7rem",
                padding: "2px 8px",
                borderRadius: 9999,
                backgroundColor: statusStyle.bg,
                color: statusStyle.text,
                fontWeight: 600,
                textTransform: "uppercase",
              }}
            >
              {exp.status}
            </span>
            <span style={{ fontSize: "0.75rem", color: "#475569" }}>
              Allocation: {(exp.allocation * 100).toFixed(0)}/{((1 - exp.allocation) * 100).toFixed(0)}
            </span>
            <span style={{ fontSize: "0.75rem", color: "#475569" }}>
              Confidence: {(exp.confidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>
        {exp.winner && (
          <div
            style={{
              fontSize: "0.75rem",
              padding: "4px 12px",
              borderRadius: 8,
              backgroundColor: "#3b1f6b",
              color: "#c4b5fd",
              fontWeight: 600,
            }}
          >
            Winner: {exp.winner}
          </div>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
        {exp.variants.map((v) => (
          <div
            key={v.name}
            style={{
              padding: "0.875rem",
              backgroundColor: v.name === exp.winner ? "#1a2744" : "#0f172a",
              borderRadius: 8,
              border: `1px solid ${v.name === exp.winner ? "#3b5998" : "#1e293b"}`,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <span style={{ fontWeight: 600, color: "#e2e8f0", fontSize: "0.875rem", textTransform: "capitalize" }}>
                {v.name}
              </span>
              <span
                style={{
                  fontSize: "0.7rem",
                  padding: "1px 6px",
                  borderRadius: 9999,
                  backgroundColor: "#1e293b",
                  color: "#94a3b8",
                }}
              >
                {v.model}
              </span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontSize: "0.75rem", color: "#64748b" }}>P@10</span>
                <span style={{ fontSize: "0.8rem", color: "#3b82f6", fontWeight: 600 }}>
                  {v.avg_precision_at_10.toFixed(3)}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontSize: "0.75rem", color: "#64748b" }}>NDCG@10</span>
                <span style={{ fontSize: "0.8rem", color: "#10b981", fontWeight: 600 }}>
                  {v.avg_ndcg_at_10.toFixed(3)}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Users</span>
                <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>{v.users_assigned}</span>
              </div>
              {v.expected_lift_percent !== 0 && (
                <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 4 }}>
                  <LiftBadge lift={v.expected_lift_percent} />
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <p style={{ fontSize: "0.7rem", color: "#334155", marginTop: 8 }}>
        Created: {new Date(exp.created_at).toLocaleString()}
      </p>
    </div>
  );
}

export default function ExperimentsPage() {
  const [experiments, setExperiments] = useState<ExperimentResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New experiment form
  const [formName, setFormName] = useState("");
  const [formDesc, setFormDesc] = useState("");
  const [formControl, setFormControl] = useState("popularity");
  const [formTreatment, setFormTreatment] = useState("collaborative_filtering");
  const [formAlloc, setFormAlloc] = useState(0.5);
  const [creating, setCreating] = useState(false);
  const [createResult, setCreateResult] = useState<string | null>(null);

  async function loadExperiments() {
    setLoading(true);
    try {
      const res = await fetchExperiments();
      if (res.success) {
        setExperiments((res as any).data?.experiments || []);
      } else {
        setError((res as any).error?.message || "Failed to load");
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadExperiments(); }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!formName.trim()) return;
    setCreating(true);
    setCreateResult(null);
    try {
      const res = await createExperiment({
        name: formName.trim(),
        description: formDesc.trim() || undefined,
        control_model: formControl,
        treatment_model: formTreatment,
        allocation: formAlloc,
      });
      if (res.success) {
        setCreateResult("Experiment created successfully.");
        setFormName(""); setFormDesc("");
        await loadExperiments();
      } else {
        setCreateResult((res as any).error?.message || "Failed");
      }
    } catch (err: any) {
      setCreateResult(err.message);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <div>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#f1f5f9" }}>A/B Experiments</h1>
        <p style={{ color: "#64748b", fontSize: "0.875rem", marginTop: 4 }}>
          Simulate A/B tests between recommendation models. User assignment is deterministic via hash.
        </p>
      </div>

      {/* New Experiment Form */}
      <div className="card" style={{ padding: "1.25rem" }}>
        <h2 style={{ fontWeight: 600, color: "#f1f5f9", marginBottom: "1rem" }}>Create Experiment</h2>
        <form onSubmit={handleCreate}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: 6 }}>
                Experiment Name
              </label>
              <input
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="e.g. cf_vs_ranker_q1"
                required
              />
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: 6 }}>
                Description (optional)
              </label>
              <input
                value={formDesc}
                onChange={(e) => setFormDesc(e.target.value)}
                placeholder="Brief description"
              />
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: 6 }}>
                Control Model
              </label>
              <select value={formControl} onChange={(e) => setFormControl(e.target.value)}>
                {MODELS.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: 6 }}>
                Treatment Model
              </label>
              <select value={formTreatment} onChange={(e) => setFormTreatment(e.target.value)}>
                {MODELS.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: 6 }}>
                Control Allocation ({(formAlloc * 100).toFixed(0)}%)
              </label>
              <input
                type="range"
                min={0.1}
                max={0.9}
                step={0.1}
                value={formAlloc}
                onChange={(e) => setFormAlloc(Number(e.target.value))}
                style={{ padding: 0, border: "none", background: "transparent" }}
              />
            </div>
            <div style={{ display: "flex", alignItems: "flex-end" }}>
              <button className="btn-primary" type="submit" disabled={creating} style={{ width: "100%" }}>
                {creating ? "Creating…" : "Create Experiment"}
              </button>
            </div>
          </div>
        </form>
        {createResult && (
          <div
            style={{
              marginTop: 12,
              padding: "0.5rem 1rem",
              borderRadius: 8,
              backgroundColor: createResult.includes("success") ? "#1d4f35" : "#3b1f1f",
              color: createResult.includes("success") ? "#4ade80" : "#f87171",
              fontSize: "0.875rem",
            }}
          >
            {createResult}
          </div>
        )}
      </div>

      {error && (
        <div style={{ padding: "0.75rem 1rem", borderRadius: 8, backgroundColor: "#3b1f1f", color: "#f87171" }}>
          {error}
        </div>
      )}

      {/* Experiments List */}
      {loading ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
          {[1, 2].map((i) => <div key={i} className="skeleton" style={{ height: 200 }} />)}
        </div>
      ) : experiments.length === 0 ? (
        <div className="card" style={{ padding: "3rem", textAlign: "center" }}>
          <p style={{ color: "#475569" }}>No experiments yet. Create one above or seed the database.</p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
          {experiments.map((exp) => (
            <ExperimentCard key={exp.experiment_id} exp={exp} />
          ))}
        </div>
      )}
    </div>
  );
}
