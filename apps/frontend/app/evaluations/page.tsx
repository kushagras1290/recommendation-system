"use client";

import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, Radar,
} from "recharts";
import { fetchEvaluations } from "@/lib/api";
import type { EvaluationResponse, ModelMetrics } from "@/lib/types";

const MODEL_COLORS: Record<string, string> = {
  popularity: "#f59e0b",
  content_based: "#3b82f6",
  collaborative_filtering: "#10b981",
  ranker: "#8b5cf6",
};

const CUSTOM_TOOLTIP_STYLE = {
  backgroundColor: "#1e293b",
  border: "1px solid #334155",
  borderRadius: 8,
  color: "#f1f5f9",
  fontSize: "0.8rem",
};

function MetricRow({ label, model, value, max }: { label: string; model: string; value: number; max: number }) {
  const color = MODEL_COLORS[model] || "#64748b";
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 6 }}>
      <span style={{ width: 80, fontSize: "0.75rem", color: "#94a3b8", flexShrink: 0 }}>{model}</span>
      <div style={{ flex: 1, height: 8, backgroundColor: "#0f172a", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", backgroundColor: color, borderRadius: 4 }} />
      </div>
      <span style={{ width: 50, textAlign: "right", fontSize: "0.8rem", color, fontWeight: 600 }}>
        {value.toFixed(3)}
      </span>
    </div>
  );
}

export default function EvaluationsPage() {
  const [data, setData] = useState<EvaluationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchEvaluations()
      .then((res) => {
        if (res.success) setData((res as any).data);
        else setError((res as any).error?.message || "Failed to load");
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        <div className="skeleton" style={{ height: 40, width: 300 }} />
        <div className="skeleton" style={{ height: 300 }} />
        <div className="skeleton" style={{ height: 300 }} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="card" style={{ padding: "2rem", textAlign: "center" }}>
        <p style={{ color: "#f87171" }}>{error}</p>
        <p style={{ color: "#475569", fontSize: "0.875rem", marginTop: 8 }}>
          Make sure models are trained (Dashboard → Train Models).
        </p>
      </div>
    );
  }

  if (!data || data.models.length === 0) {
    return (
      <div className="card" style={{ padding: "3rem", textAlign: "center" }}>
        <p style={{ color: "#475569" }}>No evaluation data. Train models first from the Dashboard.</p>
      </div>
    );
  }

  const barData = data.models.map((m) => ({
    name: m.model_name.replace("_", " "),
    "P@5": m.precision_at_5,
    "P@10": m.precision_at_10,
    "NDCG@5": m.ndcg_at_5,
    "NDCG@10": m.ndcg_at_10,
    "MRR": m.mrr,
  }));

  const radarData = [
    { metric: "P@10", ...Object.fromEntries(data.models.map((m) => [m.model_name, m.precision_at_10])) },
    { metric: "R@10", ...Object.fromEntries(data.models.map((m) => [m.model_name, m.recall_at_10])) },
    { metric: "NDCG@10", ...Object.fromEntries(data.models.map((m) => [m.model_name, m.ndcg_at_10])) },
    { metric: "MRR", ...Object.fromEntries(data.models.map((m) => [m.model_name, m.mrr])) },
    { metric: "Coverage", ...Object.fromEntries(data.models.map((m) => [m.model_name, m.coverage])) },
    { metric: "Diversity", ...Object.fromEntries(data.models.map((m) => [m.model_name, m.diversity])) },
  ];

  const maxNdcg = Math.max(...data.models.map((m) => m.ndcg_at_10));
  const maxPrec = Math.max(...data.models.map((m) => m.precision_at_10));
  const maxMrr = Math.max(...data.models.map((m) => m.mrr));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <div>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#f1f5f9" }}>Offline Metrics</h1>
        <p style={{ color: "#64748b", fontSize: "0.875rem", marginTop: 4 }}>
          Time-based split — train: {data.train_size.toLocaleString()} events · test: {data.test_size.toLocaleString()} events · {data.total_items} items
        </p>
      </div>

      {/* Summary Table */}
      <div className="card" style={{ padding: "1.25rem", overflowX: "auto" }}>
        <h2 style={{ fontWeight: 600, color: "#f1f5f9", marginBottom: "1rem" }}>Model Comparison</h2>
        <table>
          <thead>
            <tr>
              <th>Model</th>
              <th>P@5</th>
              <th>P@10</th>
              <th>R@5</th>
              <th>R@10</th>
              <th>NDCG@5</th>
              <th>NDCG@10</th>
              <th>MRR</th>
              <th>Coverage</th>
              <th>Diversity</th>
              <th>Users</th>
            </tr>
          </thead>
          <tbody>
            {data.models.map((m) => {
              const isBest = m.ndcg_at_10 === maxNdcg;
              return (
                <tr key={m.model_name}>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          backgroundColor: MODEL_COLORS[m.model_name] || "#64748b",
                          flexShrink: 0,
                        }}
                      />
                      <span style={{ fontWeight: isBest ? 700 : 400, color: isBest ? "#4ade80" : "#e2e8f0" }}>
                        {m.model_name} {isBest ? "★" : ""}
                      </span>
                    </div>
                  </td>
                  <td style={{ color: "#94a3b8" }}>{m.precision_at_5.toFixed(3)}</td>
                  <td style={{ color: "#3b82f6", fontWeight: 600 }}>{m.precision_at_10.toFixed(3)}</td>
                  <td style={{ color: "#94a3b8" }}>{m.recall_at_5.toFixed(3)}</td>
                  <td style={{ color: "#94a3b8" }}>{m.recall_at_10.toFixed(3)}</td>
                  <td style={{ color: "#94a3b8" }}>{m.ndcg_at_5.toFixed(3)}</td>
                  <td style={{ color: "#10b981", fontWeight: 600 }}>{m.ndcg_at_10.toFixed(3)}</td>
                  <td style={{ color: "#8b5cf6" }}>{m.mrr.toFixed(3)}</td>
                  <td style={{ color: "#94a3b8" }}>{m.coverage.toFixed(3)}</td>
                  <td style={{ color: "#94a3b8" }}>{m.diversity.toFixed(3)}</td>
                  <td style={{ color: "#475569" }}>{m.evaluated_users}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Charts Row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
        <div className="card" style={{ padding: "1.25rem" }}>
          <h2 style={{ fontWeight: 600, color: "#f1f5f9", marginBottom: "1rem" }}>Precision & NDCG by Model</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={barData} barCategoryGap="30%">
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 11 }} />
              <YAxis tick={{ fill: "#64748b", fontSize: 11 }} />
              <Tooltip contentStyle={CUSTOM_TOOLTIP_STYLE} />
              <Legend wrapperStyle={{ fontSize: 12, color: "#94a3b8" }} />
              <Bar dataKey="P@10" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              <Bar dataKey="NDCG@10" fill="#10b981" radius={[4, 4, 0, 0]} />
              <Bar dataKey="MRR" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card" style={{ padding: "1.25rem" }}>
          <h2 style={{ fontWeight: 600, color: "#f1f5f9", marginBottom: "1rem" }}>NDCG@10 Bar Breakdown</h2>
          <div style={{ padding: "1rem 0" }}>
            {data.models.map((m) => (
              <MetricRow key={m.model_name} label="NDCG@10" model={m.model_name} value={m.ndcg_at_10} max={maxNdcg} />
            ))}
          </div>
          <div style={{ borderTop: "1px solid #1e293b", paddingTop: "1rem", marginTop: "0.5rem" }}>
            <p style={{ fontSize: "0.75rem", color: "#475569" }}>Precision@10</p>
            {data.models.map((m) => (
              <MetricRow key={m.model_name + "_p"} label="P@10" model={m.model_name} value={m.precision_at_10} max={maxPrec} />
            ))}
          </div>
          <div style={{ borderTop: "1px solid #1e293b", paddingTop: "1rem", marginTop: "0.5rem" }}>
            <p style={{ fontSize: "0.75rem", color: "#475569" }}>MRR</p>
            {data.models.map((m) => (
              <MetricRow key={m.model_name + "_mrr"} label="MRR" model={m.model_name} value={m.mrr} max={maxMrr} />
            ))}
          </div>
        </div>
      </div>

      <p style={{ fontSize: "0.75rem", color: "#334155", textAlign: "center" }}>
        Evaluated at: {new Date(data.evaluated_at).toLocaleString()} — time-based split (80/20)
      </p>
    </div>
  );
}
