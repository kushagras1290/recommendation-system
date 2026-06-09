"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchHealth, fetchUsers, fetchEvaluations, triggerTraining } from "@/lib/api";
import type { HealthResponse, ModelStatus, User, EvaluationResponse } from "@/lib/types";

interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}

function StatCard({ label, value, sub, color = "#3b82f6" }: StatCardProps) {
  return (
    <div className="metric-card">
      <p style={{ color: "#94a3b8", fontSize: "0.8rem", marginBottom: 4 }}>{label}</p>
      <p style={{ fontSize: "2rem", fontWeight: 700, color, lineHeight: 1 }}>{value}</p>
      {sub && <p style={{ color: "#64748b", fontSize: "0.75rem", marginTop: 4 }}>{sub}</p>}
    </div>
  );
}

function ModelStatusBadge({ name, trained }: { name: string; trained: boolean }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0.625rem 0.875rem",
        backgroundColor: "#0f172a",
        borderRadius: 8,
        border: `1px solid ${trained ? "#1d4f35" : "#3b1f1f"}`,
      }}
    >
      <span style={{ fontSize: "0.875rem", color: "#cbd5e1" }}>{name}</span>
      <span
        style={{
          fontSize: "0.7rem",
          fontWeight: 600,
          padding: "2px 8px",
          borderRadius: 9999,
          backgroundColor: trained ? "#1d4f35" : "#3b1f1f",
          color: trained ? "#4ade80" : "#f87171",
        }}
      >
        {trained ? "READY" : "NOT TRAINED"}
      </span>
    </div>
  );
}

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [evaluation, setEvaluation] = useState<EvaluationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [training, setTraining] = useState(false);
  const [trainResult, setTrainResult] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [h, u, e] = await Promise.allSettled([
          fetchHealth(),
          fetchUsers(),
          fetchEvaluations(),
        ]);
        if (h.status === "fulfilled" && h.value.success)
          setHealth((h.value as any).data);
        if (u.status === "fulfilled" && u.value.success)
          setUsers(((u.value as any).data?.users as User[]) || []);
        if (e.status === "fulfilled" && e.value.success)
          setEvaluation((e.value as any).data);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function handleTrain() {
    setTraining(true);
    setTrainResult(null);
    try {
      const res = await triggerTraining();
      if (res.success) {
        const models = (res as any).data?.models || {};
        const ok = Object.values(models).filter((v) => v === "ok").length;
        setTrainResult(`Training complete — ${ok}/${Object.keys(models).length} models trained.`);
        // Reload health
        const h = await fetchHealth();
        if (h.success) setHealth((h as any).data);
      }
    } catch (err: any) {
      setTrainResult(`Error: ${err.message}`);
    } finally {
      setTraining(false);
    }
  }

  const bestModel = evaluation?.models.sort((a, b) => b.ndcg_at_10 - a.ndcg_at_10)[0];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#f1f5f9" }}>
            Recommendation System Dashboard
          </h1>
          <p style={{ color: "#64748b", fontSize: "0.875rem", marginTop: 4 }}>
            End-to-end ML pipeline — candidate generation · ranking · evaluation · A/B testing
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn-primary" onClick={handleTrain} disabled={training}>
            {training ? "Training…" : "Train Models"}
          </button>
          <Link href="/recommendations">
            <button className="btn-secondary">Get Recs</button>
          </Link>
        </div>
      </div>

      {trainResult && (
        <div
          style={{
            padding: "0.75rem 1rem",
            borderRadius: 8,
            backgroundColor: trainResult.startsWith("Error") ? "#3b1f1f" : "#1d4f35",
            color: trainResult.startsWith("Error") ? "#f87171" : "#4ade80",
            fontSize: "0.875rem",
          }}
        >
          {trainResult}
        </div>
      )}

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem" }}>
        <StatCard
          label="Total Users"
          value={loading ? "—" : users.length}
          sub="seeded for demo"
          color="#3b82f6"
        />
        <StatCard
          label="Total Items"
          value={loading ? "—" : evaluation?.total_items ?? "—"}
          sub="movies catalog"
          color="#8b5cf6"
        />
        <StatCard
          label="Training Events"
          value={loading ? "—" : evaluation?.train_size ?? "—"}
          sub="interaction logs"
          color="#10b981"
        />
        <StatCard
          label="Best NDCG@10"
          value={loading ? "—" : bestModel ? bestModel.ndcg_at_10.toFixed(3) : "—"}
          sub={bestModel ? bestModel.model_name : "train first"}
          color="#f59e0b"
        />
      </div>

      {/* Main Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
        {/* Model Status */}
        <div className="card" style={{ padding: "1.25rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
            <h2 style={{ fontWeight: 600, color: "#f1f5f9" }}>Model Registry</h2>
            <span
              style={{
                fontSize: "0.7rem",
                padding: "2px 8px",
                borderRadius: 9999,
                backgroundColor: health?.status === "ok" ? "#1d4f35" : "#3b1f1f",
                color: health?.status === "ok" ? "#4ade80" : "#f87171",
              }}
            >
              DB {health?.database || "—"}
            </span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {loading ? (
              [1, 2, 3, 4].map((i) => (
                <div key={i} className="skeleton" style={{ height: 40 }} />
              ))
            ) : (
              <>
                <ModelStatusBadge name="Popularity Baseline" trained={health?.models?.popularity ?? false} />
                <ModelStatusBadge name="Content-Based (TF-IDF)" trained={health?.models?.content_based ?? false} />
                <ModelStatusBadge name="Collaborative Filtering (SVD)" trained={health?.models?.collaborative_filtering ?? false} />
                <ModelStatusBadge name="LightGBM Ranker" trained={health?.models?.ranker ?? false} />
              </>
            )}
          </div>
          {!loading && !health?.models?.popularity && (
            <p style={{ color: "#64748b", fontSize: "0.75rem", marginTop: 12 }}>
              Click &quot;Train Models&quot; above to train all models on the seeded dataset.
            </p>
          )}
        </div>

        {/* Offline Metrics Preview */}
        <div className="card" style={{ padding: "1.25rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
            <h2 style={{ fontWeight: 600, color: "#f1f5f9" }}>Offline Metrics Preview</h2>
            <Link
              href="/evaluations"
              style={{ fontSize: "0.8rem", color: "#3b82f6" }}
            >
              Full report →
            </Link>
          </div>
          {loading ? (
            <div className="skeleton" style={{ height: 150 }} />
          ) : evaluation?.models?.length ? (
            <div style={{ overflowX: "auto" }}>
              <table>
                <thead>
                  <tr>
                    <th>Model</th>
                    <th>P@10</th>
                    <th>NDCG@10</th>
                    <th>MRR</th>
                  </tr>
                </thead>
                <tbody>
                  {evaluation.models.map((m) => (
                    <tr key={m.model_name}>
                      <td style={{ fontWeight: 500 }}>{m.model_name}</td>
                      <td style={{ color: "#3b82f6" }}>{m.precision_at_10.toFixed(3)}</td>
                      <td style={{ color: "#10b981" }}>{m.ndcg_at_10.toFixed(3)}</td>
                      <td style={{ color: "#8b5cf6" }}>{m.mrr.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ textAlign: "center", padding: "2rem", color: "#475569" }}>
              <p>No evaluation data yet.</p>
              <p style={{ fontSize: "0.8rem", marginTop: 4 }}>Train models first.</p>
            </div>
          )}
        </div>
      </div>

      {/* Quick Links */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem" }}>
        {[
          { href: "/recommendations", emoji: "🎬", title: "Explore Recs", desc: "Get personalised recommendations for any user" },
          { href: "/events", emoji: "📊", title: "Log Events", desc: "Record view, click, watch, and rating events" },
          { href: "/evaluations", emoji: "📈", title: "Metrics", desc: "Precision@K, Recall@K, NDCG@K, MRR, coverage, diversity" },
          { href: "/experiments", emoji: "🧪", title: "A/B Tests", desc: "Compare models and view expected lift" },
        ].map((item) => (
          <Link key={item.href} href={item.href}>
            <div
              className="card card-hover"
              style={{ padding: "1.25rem", cursor: "pointer" }}
            >
              <div style={{ fontSize: "1.75rem", marginBottom: 8 }}>{item.emoji}</div>
              <h3 style={{ fontWeight: 600, color: "#f1f5f9", marginBottom: 4 }}>{item.title}</h3>
              <p style={{ fontSize: "0.8rem", color: "#64748b", lineHeight: 1.4 }}>{item.desc}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
