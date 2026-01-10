import { useEffect, useMemo, useState } from "react";
import { parseReceipt, saveReceipt, listReceipts, getInsights } from "./api";

function cn(...xs) {
  return xs.filter(Boolean).join(" ");
}

function Pill({ active, children, onClick }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "px-3 py-2 rounded-full text-sm font-medium transition",
        active
          ? "bg-black text-white shadow"
          : "bg-white text-gray-700 border border-gray-200 hover:bg-gray-50"
      )}
      type="button"
    >
      {children}
    </button>
  );
}

function StatCard({ label, value, sub }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="text-xs font-medium text-gray-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-gray-900">{value}</div>
      {sub ? <div className="mt-1 text-xs text-gray-500">{sub}</div> : null}
    </div>
  );
}

function Money({ v }) {
  if (v === null || v === undefined) return <span className="text-gray-400">—</span>;
  return <span>${Number(v).toFixed(2)}</span>;
}

export default function App() {
  const [tab, setTab] = useState("scan"); // scan | history | insights
  const [file, setFile] = useState(null);

  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const [preview, setPreview] = useState(null); // output from /receipts/parse
  const [savedId, setSavedId] = useState(null);

  const [receipts, setReceipts] = useState([]);
  const [insights, setInsights] = useState(null);

  const hasPreview = !!preview;

  async function refreshReceipts() {
    const rows = await listReceipts();
    setReceipts(rows);
  }

  async function refreshInsights() {
    const data = await getInsights("week");
    setInsights(data);
  }

  useEffect(() => {
    // Load initial data when you switch tabs
    (async () => {
      try {
        setErr("");
        if (tab === "history") await refreshReceipts();
        if (tab === "insights") await refreshInsights();
      } catch (e) {
        setErr(e.message || "Something went wrong");
      }
    })();
  }, [tab]);

  const canSave = useMemo(() => {
    if (!preview) return false;
    return !!preview.merchant && (preview.total ?? 0) > 0 && !!preview.category;
  }, [preview]);

  async function onScan() {
    if (!file) return;
    setLoading(true);
    setErr("");
    setSavedId(null);

    try {
      const data = await parseReceipt(file);
      setPreview(data);
      setTab("scan");
    } catch (e) {
      setErr(e.message || "Parse failed");
    } finally {
      setLoading(false);
    }
  }

  async function onSave() {
    if (!preview) return;
    setLoading(true);
    setErr("");

    try {
      // Your backend SaveReceiptRequest expects: merchant, date, total, tax, category
      const payload = {
        merchant: preview.merchant,
        date: preview.date ?? null,
        total: preview.total,
        tax: preview.tax ?? null,
        category: preview.category,
      };

      const res = await saveReceipt(payload);
      setSavedId(res.receipt_id || res.receiptId || res.id || "saved");
      await refreshReceipts();
    } catch (e) {
      setErr(e.message || "Save failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top bar */}
      <div className="sticky top-0 z-10 border-b border-gray-200 bg-white/80 backdrop-blur">
        <div className="mx-auto max-w-md px-4 py-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-lg font-semibold text-gray-900">Receipt Story</div>
              <div className="text-xs text-gray-500">Scan → Save → Insights</div>
            </div>
            <div className="flex gap-2">
              <Pill active={tab === "scan"} onClick={() => setTab("scan")}>Scan</Pill>
              <Pill active={tab === "history"} onClick={() => setTab("history")}>History</Pill>
              <Pill active={tab === "insights"} onClick={() => setTab("insights")}>Insights</Pill>
            </div>
          </div>
        </div>
      </div>

      {/* Main */}
      <div className="mx-auto max-w-md px-4 py-6">
        {err ? (
          <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {err}
          </div>
        ) : null}

        {/* SCAN TAB */}
        {tab === "scan" && (
          <div className="space-y-4">
            <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
              <div className="text-sm font-medium text-gray-900">1) Capture a receipt</div>
              <div className="mt-2 text-xs text-gray-500">
                Use your phone camera or upload an image. Then hit “Parse”.
              </div>

              <div className="mt-3">
                <input
                  type="file"
                  accept="image/*"
                  capture="environment"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="block w-full text-sm text-gray-700
                             file:mr-3 file:rounded-lg file:border-0
                             file:bg-gray-900 file:px-3 file:py-2 file:text-white
                             hover:file:bg-black"
                />
              </div>

              <div className="mt-3 flex gap-2">
                <button
                  onClick={onScan}
                  disabled={!file || loading}
                  className={cn(
                    "flex-1 rounded-xl px-4 py-3 text-sm font-semibold text-white shadow-sm",
                    !file || loading ? "bg-gray-300" : "bg-black hover:bg-gray-900"
                  )}
                  type="button"
                >
                  {loading ? "Parsing..." : "Parse Receipt"}
                </button>

                <button
                  onClick={() => {
                    setPreview(null);
                    setSavedId(null);
                    setErr("");
                    setFile(null);
                  }}
                  className="rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-semibold text-gray-800 hover:bg-gray-50"
                  type="button"
                >
                  Reset
                </button>
              </div>
            </div>

            {hasPreview && (
              <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="text-sm font-semibold text-gray-900">2) Preview</div>
                    <div className="mt-1 text-xs text-gray-500">
                      Verify fields before saving.
                    </div>
                  </div>
                  {savedId ? (
                    <span className="rounded-full bg-green-50 px-3 py-1 text-xs font-semibold text-green-700 border border-green-200">
                      Saved ✓
                    </span>
                  ) : null}
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3">
                  <StatCard label="Merchant" value={preview.merchant || "—"} />
                  <StatCard label="Date" value={preview.date || "—"} />
                  <StatCard label="Total" value={<Money v={preview.total} />} />
                  <StatCard label="Tax" value={<Money v={preview.tax} />} />
                  <StatCard label="Subtotal" value={<Money v={preview.subtotal} />} />
                  <StatCard label="Category" value={preview.category || "—"} />
                </div>

                <div className="mt-4">
                  <div className="text-xs font-medium text-gray-500">Items</div>
                  <div className="mt-2 space-y-2">
                    {(preview.items || []).length ? (
                      preview.items.map((it, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between rounded-xl border border-gray-100 bg-gray-50 px-3 py-2"
                        >
                          <div className="text-sm text-gray-900">{it.description}</div>
                          <div className="text-xs text-gray-500">
                            {it.total_price != null ? <Money v={it.total_price} /> : ""}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-sm text-gray-400">No line items detected.</div>
                    )}
                  </div>
                </div>

                <div className="mt-4 flex gap-2">
                  <button
                    onClick={onSave}
                    disabled={!canSave || loading}
                    className={cn(
                      "flex-1 rounded-xl px-4 py-3 text-sm font-semibold text-white shadow-sm",
                      !canSave || loading ? "bg-gray-300" : "bg-black hover:bg-gray-900"
                    )}
                    type="button"
                  >
                    {loading ? "Saving..." : "Save to History"}
                  </button>

                  <button
                    onClick={() => setTab("history")}
                    className="rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-semibold text-gray-800 hover:bg-gray-50"
                    type="button"
                  >
                    View History →
                  </button>
                </div>

                <details className="mt-4">
                  <summary className="cursor-pointer text-xs font-medium text-gray-500">
                    Debug raw_text
                  </summary>
                  <pre className="mt-2 max-h-48 overflow-auto rounded-xl bg-gray-900 p-3 text-xs text-gray-100">
{preview.raw_text || ""}
                  </pre>
                </details>
              </div>
            )}
          </div>
        )}

        {/* HISTORY TAB */}
        {tab === "history" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-sm font-semibold text-gray-900">Receipt History</div>
              <button
                onClick={() => refreshReceipts().catch((e) => setErr(e.message))}
                className="text-xs font-semibold text-gray-700 hover:text-black"
                type="button"
              >
                Refresh
              </button>
            </div>

            {receipts.length ? (
              receipts.map((r) => (
                <div key={r.id} className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="text-sm font-semibold text-gray-900">{r.merchant}</div>
                      <div className="mt-1 text-xs text-gray-500">{r.date || "—"} • {r.category}</div>
                    </div>
                    <div className="text-sm font-semibold text-gray-900">
                      <Money v={r.total} />
                    </div>
                  </div>
                  <div className="mt-2 text-xs text-gray-500">
                    Tax: <Money v={r.tax} /> • Saved: {r.created_at || "—"}
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-gray-200 bg-white p-6 text-sm text-gray-500 shadow-sm">
                No receipts yet. Go to Scan and save one.
              </div>
            )}
          </div>
        )}

        {/* INSIGHTS TAB */}
        {tab === "insights" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-sm font-semibold text-gray-900">Weekly Insights</div>
              <button
                onClick={() => refreshInsights().catch((e) => setErr(e.message))}
                className="text-xs font-semibold text-gray-700 hover:text-black"
                type="button"
              >
                Refresh
              </button>
            </div>

            {insights ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <StatCard label="Receipts" value={insights.receipt_count} />
                  <StatCard label="Total spend" value={`$${Number(insights.total_spend).toFixed(2)}`} />
                </div>

                <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                  <div className="text-sm font-semibold text-gray-900">Spend by category</div>
                  <div className="mt-3 space-y-2">
                    {Object.entries(insights.spend_by_category || {}).map(([k, v]) => (
                      <div key={k} className="flex items-center justify-between">
                        <div className="text-sm text-gray-700">{k}</div>
                        <div className="text-sm font-semibold text-gray-900">
                          ${Number(v).toFixed(2)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                  <div className="text-sm font-semibold text-gray-900">Story</div>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-gray-700">
                    {(insights.story_insights || []).map((s, i) => <li key={i}>{s}</li>)}
                  </ul>
                  <div className="mt-3 rounded-xl bg-gray-50 p-3 text-sm font-medium text-gray-900">
                    {insights.recommendation}
                  </div>
                </div>
              </div>
            ) : (
              <div className="rounded-2xl border border-gray-200 bg-white p-6 text-sm text-gray-500 shadow-sm">
                No insights yet — add a few receipts first.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
