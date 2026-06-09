"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchEvents, recordEvent } from "@/lib/api";
import type { EventResponse } from "@/lib/types";

const EVENT_TYPES = ["view", "click", "watch", "rate_positive", "rate_negative", "wishlist"];
const EVENT_WEIGHTS: Record<string, number> = {
  view: 0.3, click: 0.5, watch: 1.0,
  rate_positive: 1.5, rate_negative: -0.5, wishlist: 0.8,
};
const EVENT_COLORS: Record<string, string> = {
  view: "#94a3b8", click: "#3b82f6", watch: "#10b981",
  rate_positive: "#f59e0b", rate_negative: "#ef4444", wishlist: "#8b5cf6",
};

function WeightBadge({ weight }: { weight: number }) {
  const color = weight > 0 ? (weight >= 1 ? "#4ade80" : "#60a5fa") : "#f87171";
  return (
    <span
      style={{
        fontSize: "0.75rem",
        padding: "1px 8px",
        borderRadius: 9999,
        backgroundColor: color + "22",
        color,
        fontWeight: 600,
      }}
    >
      {weight > 0 ? "+" : ""}{weight}
    </span>
  );
}

export default function EventsPage() {
  const [events, setEvents] = useState<EventResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);

  // Form state
  const [formUser, setFormUser] = useState("");
  const [formItem, setFormItem] = useState("");
  const [formEventType, setFormEventType] = useState("watch");
  const [submitting, setSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState<{ ok: boolean; msg: string } | null>(null);

  const loadEvents = useCallback(async (p = page) => {
    setLoading(true);
    try {
      const res = await fetchEvents(p, 20);
      if (res.success) {
        setEvents(res.data);
        setTotal(res.meta.total);
        setTotalPages(res.meta.total_pages);
      }
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => { loadEvents(page); }, [loadEvents, page]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formUser.trim() || !formItem.trim()) return;
    setSubmitting(true);
    setSubmitResult(null);
    try {
      const res = await recordEvent({
        user_external_id: formUser.trim(),
        item_external_id: formItem.trim(),
        event_type: formEventType,
      });
      if (res.success) {
        setSubmitResult({ ok: true, msg: `Event recorded (weight: ${(res as any).data.weight})` });
        setFormUser(""); setFormItem("");
        loadEvents(1);
        setPage(1);
      } else {
        setSubmitResult({ ok: false, msg: (res as any).error?.message || "Failed" });
      }
    } catch (err: any) {
      setSubmitResult({ ok: false, msg: err.message });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <div>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#f1f5f9" }}>Event Log</h1>
        <p style={{ color: "#64748b", fontSize: "0.875rem", marginTop: 4 }}>
          User interaction events — views, clicks, watches, ratings, wishlists.
        </p>
      </div>

      {/* Log Event Form */}
      <div className="card" style={{ padding: "1.25rem" }}>
        <h2 style={{ fontWeight: 600, color: "#f1f5f9", marginBottom: "1rem" }}>Log New Event</h2>
        <form onSubmit={handleSubmit}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr auto", gap: "1rem", alignItems: "end" }}>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: 6 }}>
                User ID (e.g. user_001)
              </label>
              <input
                value={formUser}
                onChange={(e) => setFormUser(e.target.value)}
                placeholder="user_001"
                required
              />
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: 6 }}>
                Item ID (e.g. movie_001)
              </label>
              <input
                value={formItem}
                onChange={(e) => setFormItem(e.target.value)}
                placeholder="movie_001"
                required
              />
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: 6 }}>
                Event Type
              </label>
              <select value={formEventType} onChange={(e) => setFormEventType(e.target.value)}>
                {EVENT_TYPES.map((et) => (
                  <option key={et} value={et}>
                    {et} (weight: {EVENT_WEIGHTS[et]})
                  </option>
                ))}
              </select>
            </div>
            <button className="btn-primary" type="submit" disabled={submitting}>
              {submitting ? "Logging…" : "Log Event"}
            </button>
          </div>
        </form>

        {submitResult && (
          <div
            style={{
              marginTop: 12,
              padding: "0.5rem 1rem",
              borderRadius: 8,
              backgroundColor: submitResult.ok ? "#1d4f35" : "#3b1f1f",
              color: submitResult.ok ? "#4ade80" : "#f87171",
              fontSize: "0.875rem",
            }}
          >
            {submitResult.msg}
          </div>
        )}

        <div style={{ marginTop: 12 }}>
          <p style={{ fontSize: "0.75rem", color: "#475569" }}>
            Event weights: view (0.3) · click (0.5) · watch (1.0) · rate_positive (1.5) · rate_negative (−0.5) · wishlist (0.8)
          </p>
        </div>
      </div>

      {/* Event Table */}
      <div className="card" style={{ padding: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <h2 style={{ fontWeight: 600, color: "#f1f5f9" }}>
            Recent Events <span style={{ color: "#64748b", fontWeight: 400 }}>({total.toLocaleString()} total)</span>
          </h2>
          <button className="btn-secondary" onClick={() => loadEvents(page)}>Refresh</button>
        </div>

        {loading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {[1, 2, 3, 4, 5].map((i) => <div key={i} className="skeleton" style={{ height: 44 }} />)}
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>User</th>
                  <th>Item</th>
                  <th>Event</th>
                  <th>Weight</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {events.map((ev) => (
                  <tr key={ev.id}>
                    <td style={{ color: "#475569", fontSize: "0.75rem" }}>#{ev.id}</td>
                    <td style={{ fontWeight: 500, color: "#93c5fd" }}>{ev.user_external_id}</td>
                    <td style={{ color: "#e2e8f0" }}>{ev.item_external_id}</td>
                    <td>
                      <span
                        style={{
                          fontSize: "0.75rem",
                          padding: "2px 8px",
                          borderRadius: 9999,
                          backgroundColor: (EVENT_COLORS[ev.event_type] || "#64748b") + "22",
                          color: EVENT_COLORS[ev.event_type] || "#64748b",
                          fontWeight: 500,
                        }}
                      >
                        {ev.event_type}
                      </span>
                    </td>
                    <td><WeightBadge weight={ev.weight} /></td>
                    <td style={{ color: "#64748b", fontSize: "0.8rem" }}>
                      {new Date(ev.timestamp).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 16 }}>
            <button
              className="btn-secondary"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              ← Prev
            </button>
            <span style={{ padding: "0.5rem 0.75rem", color: "#94a3b8", fontSize: "0.875rem" }}>
              {page} / {totalPages}
            </span>
            <button
              className="btn-secondary"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
            >
              Next →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
