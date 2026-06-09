"use client";

import { useEffect, useState } from "react";
import { fetchUsers, fetchRecommendations } from "@/lib/api";
import type { User, RecommendationItem } from "@/lib/types";

const MODELS = ["auto", "popularity", "content_based", "collaborative_filtering", "ranker"];

const CATEGORY_COLORS: Record<string, string> = {
  Action: "#ef4444", Animation: "#f59e0b", Comedy: "#22c55e",
  Crime: "#8b5cf6", Documentary: "#06b6d4", Drama: "#3b82f6",
  Fantasy: "#a78bfa", Horror: "#dc2626", Romance: "#ec4899",
  "Sci-Fi": "#0ea5e9", Thriller: "#f97316", War: "#6b7280", Western: "#92400e",
};

function RecCard({ rec }: { rec: RecommendationItem }) {
  const color = CATEGORY_COLORS[rec.category] || "#64748b";
  const rating = rec.attributes?.rating;
  const year = rec.attributes?.year;
  const description = rec.attributes?.description;

  return (
    <div
      className="card"
      style={{ padding: "1rem", display: "flex", gap: "1rem", alignItems: "flex-start" }}
    >
      <div
        style={{
          flexShrink: 0,
          width: 40,
          height: 40,
          borderRadius: 8,
          backgroundColor: color + "22",
          border: `1px solid ${color}44`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontWeight: 700,
          color,
          fontSize: "1rem",
        }}
      >
        #{rec.rank}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
          <h3 style={{ fontWeight: 600, color: "#f1f5f9", fontSize: "0.9rem", lineHeight: 1.3 }}>
            {rec.title}
          </h3>
          <div style={{ display: "flex", gap: 4, flexShrink: 0 }}>
            {year && (
              <span style={{ fontSize: "0.7rem", color: "#94a3b8" }}>{year}</span>
            )}
            {rating && (
              <span style={{ fontSize: "0.7rem", color: "#f59e0b", fontWeight: 600 }}>
                * {rating.toFixed(1)}
              </span>
            )}
          </div>
        </div>
        <div style={{ display: "flex", gap: 6, marginTop: 4, flexWrap: "wrap", alignItems: "center" }}>
          <span
            style={{
              fontSize: "0.65rem",
              padding: "1px 7px",
              borderRadius: 9999,
              backgroundColor: color + "22",
              color,
              fontWeight: 500,
            }}
          >
            {rec.category}
          </span>
          <span style={{ fontSize: "0.75rem", color: "#64748b" }}>{rec.explanation}</span>
        </div>
        {description && (
          <p style={{ fontSize: "0.75rem", color: "#475569", marginTop: 4, lineHeight: 1.4 }}>
            {description.length > 100 ? `${description.slice(0, 100)}...` : description}
          </p>
        )}
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6 }}>
          <span style={{ fontSize: "0.7rem", color: "#475569" }}>
            score: {rec.score.toFixed(4)}
          </span>
          <span
            style={{
              fontSize: "0.65rem",
              padding: "1px 7px",
              borderRadius: 9999,
              backgroundColor: "#1e3a5f",
              color: "#93c5fd",
            }}
          >
            {rec.model_version}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function RecommendationsPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUser, setSelectedUser] = useState("");
  const [model, setModel] = useState("auto");
  const [k, setK] = useState(10);
  const [recs, setRecs] = useState<RecommendationItem[]>([]);
  const [modelUsed, setModelUsed] = useState("");
  const [isColdStart, setIsColdStart] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingUsers, setLoadingUsers] = useState(true);

  useEffect(() => {
    fetchUsers()
      .then((res) => {
        if (res.success) {
          const fetchedUsers = res.data.users;
          setUsers(fetchedUsers);
          if (fetchedUsers.length) {
            setSelectedUser(fetchedUsers[0].external_id);
          }
        }
      })
      .finally(() => setLoadingUsers(false));
  }, []);

  async function handleFetch() {
    if (!selectedUser) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchRecommendations(selectedUser, k, model);
      if (res.success) {
        setRecs(res.data.recommendations);
        setModelUsed(res.data.model_used);
        setIsColdStart(res.data.is_cold_start);
      } else {
        setError(res.error.message || "Failed to fetch recommendations");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  const selectedUserObj = users.find((u) => u.external_id === selectedUser);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <div>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#f1f5f9" }}>
          Recommendations Explorer
        </h1>
        <p style={{ color: "#64748b", fontSize: "0.875rem", marginTop: 4 }}>
          Get personalised recommendations for any user across all models.
        </p>
      </div>

      {/* Controls */}
      <div className="card" style={{ padding: "1.25rem" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 120px auto", gap: "1rem", alignItems: "end" }}>
          <div>
            <label style={{ fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: 6 }}>
              User
            </label>
            <select value={selectedUser} onChange={(e) => setSelectedUser(e.target.value)} disabled={loadingUsers}>
              {loadingUsers ? (
                <option>Loading...</option>
              ) : (
                users.map((u) => (
                  <option key={u.external_id} value={u.external_id}>
                    {u.external_id} ({u.segment})
                  </option>
                ))
              )}
            </select>
          </div>
          <div>
            <label style={{ fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: 6 }}>
              Model
            </label>
            <select value={model} onChange={(e) => setModel(e.target.value)}>
              {MODELS.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
          <div>
            <label style={{ fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: 6 }}>
              K (results)
            </label>
            <input
              type="number"
              min={1}
              max={50}
              value={k}
              onChange={(e) => setK(Number(e.target.value))}
            />
          </div>
          <button className="btn-primary" onClick={handleFetch} disabled={loading || !selectedUser}>
            {loading ? "Loading..." : "Get Recommendations"}
          </button>
        </div>

        {selectedUserObj && (
          <div style={{ marginTop: 12, display: "flex", gap: 12, alignItems: "center" }}>
            <span style={{ fontSize: "0.8rem", color: "#64748b" }}>
              Segment:
            </span>
            <span
              style={{
                fontSize: "0.75rem",
                padding: "2px 10px",
                borderRadius: 9999,
                backgroundColor: "#1e3a5f",
                color: "#93c5fd",
                fontWeight: 500,
              }}
            >
              {selectedUserObj.segment}
            </span>
            {isColdStart && recs.length > 0 && (
              <span
                style={{
                  fontSize: "0.75rem",
                  padding: "2px 10px",
                  borderRadius: 9999,
                  backgroundColor: "#3b2a1d",
                  color: "#fbbf24",
                }}
              >
                Cold-start - showing popular items
              </span>
            )}
            {modelUsed && recs.length > 0 && !isColdStart && (
              <span
                style={{
                  fontSize: "0.75rem",
                  padding: "2px 10px",
                  borderRadius: 9999,
                  backgroundColor: "#1d3a1f",
                  color: "#4ade80",
                }}
              >
                Served by: {modelUsed}
              </span>
            )}
          </div>
        )}
      </div>

      {error && (
        <div style={{ padding: "0.75rem 1rem", borderRadius: 8, backgroundColor: "#3b1f1f", color: "#f87171" }}>
          {error}
        </div>
      )}

      {/* Results */}
      {loading ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton" style={{ height: 120 }} />
          ))}
        </div>
      ) : recs.length > 0 ? (
        <>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2 style={{ fontWeight: 600, color: "#f1f5f9" }}>
              {recs.length} recommendations for <span style={{ color: "#3b82f6" }}>{selectedUser}</span>
            </h2>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            {recs.map((rec) => (
              <RecCard key={rec.item_id} rec={rec} />
            ))}
          </div>
        </>
      ) : (
        <div className="card" style={{ padding: "3rem", textAlign: "center" }}>
          <p style={{ color: "#475569", fontSize: "1rem" }}>
            Select a user and click &quot;Get Recommendations&quot;
          </p>
          <p style={{ color: "#334155", fontSize: "0.8rem", marginTop: 8 }}>
            If models are not trained yet, go to the Dashboard and click &quot;Train Models&quot; first.
          </p>
        </div>
      )}
    </div>
  );
}
