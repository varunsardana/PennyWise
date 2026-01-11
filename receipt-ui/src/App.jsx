import { useEffect, useMemo, useState } from "react";
import { parseReceipt, saveReceipt, listReceipts, getInsights, getTrends, getChartsData } from "./api";
import {
  PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  LineChart, Line
} from "recharts";

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
  const [trends, setTrends] = useState(null);
  const [chartsData, setChartsData] = useState(null);
  const [trendsPeriod, setTrendsPeriod] = useState("weekly");
  const [customStartDate, setCustomStartDate] = useState("");
  const [customEndDate, setCustomEndDate] = useState("");

  // Colors for pie chart
  const COLORS = ["#8b5cf6", "#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#ec4899", "#6366f1", "#84cc16"];

  const hasPreview = !!preview;

  async function refreshReceipts() {
    const rows = await listReceipts();
    setReceipts(rows);
  }

  async function refreshInsights() {
    const data = await getInsights("week");
    setInsights(data);
  }

  async function refreshTrends(period = trendsPeriod, startDate = null, endDate = null) {
    const data = await getTrends(period, startDate, endDate);
    setTrends(data);
  }

  async function refreshChartsData(period = trendsPeriod) {
    const data = await getChartsData(period);
    setChartsData(data);
  }

  useEffect(() => {
    // Load initial data when you switch tabs
    (async () => {
      try {
        setErr("");
        if (tab === "history") await refreshReceipts();
        if (tab === "insights") await refreshInsights();
        if (tab === "trends") {
          await refreshTrends();
          await refreshInsights();
          await refreshChartsData();
        }
      } catch (e) {
        setErr(e.message || "Something went wrong");
      }
    })();
  }, [tab]);

  // Refresh trends and charts when period changes
  useEffect(() => {
    if (tab === "trends") {
      refreshTrends(trendsPeriod).catch((e) => setErr(e.message));
      refreshChartsData(trendsPeriod).catch((e) => setErr(e.message));
    }
  }, [trendsPeriod]);

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
        <div className="mx-auto max-w-md md:max-w-lg px-4 py-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-lg font-semibold text-gray-900">Receipt Story</div>
              <div className="text-xs text-gray-500">Scan → Save → Trends</div>
            </div>
            <div className="flex gap-2">
              <Pill active={tab === "scan"} onClick={() => setTab("scan")}>Scan</Pill>
              <Pill active={tab === "history"} onClick={() => setTab("history")}>History</Pill>
              <Pill active={tab === "trends"} onClick={() => setTab("trends")}>Trends</Pill>
            </div>
          </div>
        </div>
      </div>

      {/* Main */}
      <div className="mx-auto max-w-md md:max-w-lg px-4 py-6">
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

        {/* TRENDS TAB */}
        {tab === "trends" && (
          <div className="space-y-4">
            {/* Period Toggle - Apple Health Style */}
            <div className="flex justify-center">
              <div className="inline-flex rounded-xl bg-gray-100 p-1 flex-wrap gap-1">
                {["daily", "weekly", "monthly", "yearly", "all"].map((p) => (
                  <button
                    key={p}
                    onClick={() => setTrendsPeriod(p)}
                    className={cn(
                      "px-3 py-2 rounded-lg text-sm font-medium transition",
                      trendsPeriod === p
                        ? "bg-white text-gray-900 shadow"
                        : "text-gray-600 hover:text-gray-900"
                    )}
                    type="button"
                  >
                    {p === "all" ? "All Time" : p.charAt(0).toUpperCase() + p.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {/* Custom Date Range Inputs - hidden for now, using All Time instead */}
            {false && trendsPeriod === "custom" && (
              <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                <div className="text-sm font-semibold text-gray-900 mb-3">Custom Date Range</div>
                <div className="flex gap-3 items-end">
                  <div className="flex-1">
                    <label className="text-xs text-gray-500">Start Date</label>
                    <input
                      type="date"
                      value={customStartDate}
                      onChange={(e) => setCustomStartDate(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                    />
                  </div>
                  <div className="flex-1">
                    <label className="text-xs text-gray-500">End Date</label>
                    <input
                      type="date"
                      value={customEndDate}
                      onChange={(e) => setCustomEndDate(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                    />
                  </div>
                  <button
                    onClick={() => refreshTrends("custom", customStartDate, customEndDate).catch((e) => setErr(e.message))}
                    disabled={!customStartDate || !customEndDate}
                    className={cn(
                      "px-4 py-2 rounded-lg text-sm font-medium",
                      customStartDate && customEndDate
                        ? "bg-black text-white hover:bg-gray-900"
                        : "bg-gray-200 text-gray-400"
                    )}
                    type="button"
                  >
                    Apply
                  </button>
                </div>
              </div>
            )}

            {trends ? (
              <div className="space-y-4">
                {/* Summary Stats */}
                <div className="grid grid-cols-2 gap-3">
                  <StatCard
                    label="Total Spend"
                    value={`$${Number(trends.total_spend).toFixed(2)}`}
                  />
                  <StatCard
                    label="Receipts"
                    value={trends.receipt_count}
                  />
                </div>

                {/* Comparison Card */}
                {trends.comparison && (
                  <div className={cn(
                    "rounded-2xl border p-4 shadow-sm",
                    trends.comparison.direction === "up"
                      ? "border-red-200 bg-red-50"
                      : trends.comparison.direction === "down"
                      ? "border-green-200 bg-green-50"
                      : "border-gray-200 bg-white"
                  )}>
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">
                        {trends.comparison.direction === "up" ? "📈" :
                         trends.comparison.direction === "down" ? "📉" : "➡️"}
                      </span>
                      <div>
                        <div className="text-sm font-semibold text-gray-900">
                          {trends.comparison.message}
                        </div>
                        <div className="text-xs text-gray-500">
                          {trends.period_start} to {trends.period_end}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Pie Chart */}
                {Object.keys(trends.spend_by_category || {}).length > 0 ? (
                  <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                    <div className="text-sm font-semibold text-gray-900 mb-4">
                      Spending by Category
                    </div>
                    <ResponsiveContainer width="100%" height={300}>
                      <PieChart>
                        <Pie
                          data={Object.entries(trends.spend_by_category).map(([name, value]) => ({
                            name,
                            value: Number(value),
                          }))}
                          cx="50%"
                          cy="50%"
                          innerRadius={50}
                          outerRadius={90}
                          paddingAngle={2}
                          dataKey="value"
                          label={({ name, percent, cx, cy, midAngle, outerRadius, index }) => {
                            const RADIAN = Math.PI / 180;
                            const radius = outerRadius + 25;
                            const x = cx + radius * Math.cos(-midAngle * RADIAN);
                            const y = cy + radius * Math.sin(-midAngle * RADIAN);
                            return (
                              <text
                                x={x}
                                y={y}
                                fill={COLORS[index % COLORS.length]}
                                textAnchor={x > cx ? 'start' : 'end'}
                                dominantBaseline="central"
                                style={{ fontSize: '14px', fontWeight: '600' }}
                              >
                                {`${name} ${(percent * 100).toFixed(0)}%`}
                              </text>
                            );
                          }}
                          labelLine={false}
                        >
                          {Object.entries(trends.spend_by_category).map((_, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(value) => `$${Number(value).toFixed(2)}`}
                        />
                      </PieChart>
                    </ResponsiveContainer>

                    {/* Category Legend with amounts */}
                    <div className="mt-4 space-y-2">
                      {Object.entries(trends.spend_by_category).map(([cat, amount], idx) => (
                        <div key={cat} className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <div
                              className="w-3 h-3 rounded-full"
                              style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                            />
                            <span className="text-sm text-gray-700">{cat}</span>
                          </div>
                          <span className="text-sm font-semibold text-gray-900">
                            ${Number(amount).toFixed(2)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-gray-200 bg-white p-6 text-center shadow-sm">
                    <div className="text-4xl mb-2">📊</div>
                    <div className="text-sm text-gray-500">
                      No spending data for this period.
                    </div>
                    <div className="text-xs text-gray-400 mt-1">
                      Add some receipts to see your trends!
                    </div>
                  </div>
                )}

                {/* Spending Over Time Chart */}
                {chartsData?.spending_over_time?.length > 0 && (
                  <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                    <div className="text-sm font-semibold text-gray-900 mb-4">
                      Spending Over Time
                    </div>
                    <ResponsiveContainer width="100%" height={250}>
                      <BarChart data={chartsData.spending_over_time}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                        <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `$${v}`} />
                        <Tooltip formatter={(value) => `$${Number(value).toFixed(2)}`} />
                        <Bar dataKey="amount" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}

                {/* Top Merchants Chart */}
                {chartsData?.top_merchants?.length > 0 && (
                  <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                    <div className="text-sm font-semibold text-gray-900 mb-4">
                      Top Merchants
                    </div>
                    <ResponsiveContainer width="100%" height={Math.max(200, chartsData.top_merchants.length * 40)}>
                      <BarChart data={chartsData.top_merchants} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis type="number" tick={{ fontSize: 12 }} tickFormatter={(v) => `$${v}`} />
                        <YAxis type="category" dataKey="merchant" tick={{ fontSize: 12 }} width={100} />
                        <Tooltip
                          formatter={(value, name) => [`$${Number(value).toFixed(2)}`, "Total"]}
                          labelFormatter={(label) => label}
                        />
                        <Bar dataKey="amount" fill="#06b6d4" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}

                {/* Category Trends Chart */}
                {chartsData?.category_trends?.length > 0 && (
                  <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                    <div className="text-sm font-semibold text-gray-900 mb-4">
                      Category Trends
                    </div>
                    <ResponsiveContainer width="100%" height={250}>
                      <LineChart data={chartsData.category_trends}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                        <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `$${v}`} />
                        <Tooltip formatter={(value) => `$${Number(value).toFixed(2)}`} />
                        {chartsData.category_trends[0] &&
                          Object.keys(chartsData.category_trends[0].categories || {}).map((cat, idx) => (
                            <Line
                              key={cat}
                              type="monotone"
                              dataKey={`categories.${cat}`}
                              name={cat}
                              stroke={COLORS[idx % COLORS.length]}
                              strokeWidth={2}
                              dot={{ r: 4 }}
                            />
                          ))}
                      </LineChart>
                    </ResponsiveContainer>
                    {/* Legend for categories */}
                    <div className="mt-3 flex flex-wrap gap-3 justify-center">
                      {chartsData.category_trends[0] &&
                        Object.keys(chartsData.category_trends[0].categories || {}).map((cat, idx) => (
                          <div key={cat} className="flex items-center gap-1">
                            <div
                              className="w-3 h-3 rounded-full"
                              style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                            />
                            <span className="text-xs text-gray-600">{cat}</span>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                {/* Day of Week Chart */}
                {chartsData?.day_of_week?.length > 0 && (
                  <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                    <div className="text-sm font-semibold text-gray-900 mb-4">
                      Spending by Day of Week
                    </div>
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={chartsData.day_of_week}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis dataKey="day" tick={{ fontSize: 12 }} />
                        <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `$${v}`} />
                        <Tooltip
                          formatter={(value, name) => [`$${Number(value).toFixed(2)}`, "Total"]}
                        />
                        <Bar dataKey="amount" fill="#10b981" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}

                {/* Story Section */}
                {insights && (
                  <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                    <div className="text-sm font-semibold text-gray-900">Story</div>
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-gray-700">
                      {(insights.story_insights || []).map((s, i) => <li key={i}>{s}</li>)}
                    </ul>
                    <div className="mt-3 rounded-xl bg-gray-50 p-3 text-sm font-medium text-gray-900">
                      {insights.recommendation}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="rounded-2xl border border-gray-200 bg-white p-6 text-sm text-gray-500 shadow-sm text-center">
                Loading trends...
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
