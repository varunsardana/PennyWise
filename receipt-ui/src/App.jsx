import { useEffect, useMemo, useState, useRef } from "react";
import { parseReceipt, saveReceipt, listReceipts, getInsights, getTrends, getChartsData, deleteReceipt, updateReceipt, sendChatMessage } from "./api";
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
        "px-6 py-3 rounded-full text-base font-semibold transition-all duration-200",
        active
          ? "bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-lg"
          : "bg-white text-gray-600 border border-gray-200 hover:border-gray-300 hover:text-gray-900 hover:shadow"
      )}
      type="button"
    >
      {children}
    </button>
  );
}

function StatCard({ label, value, sub }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="text-base font-medium text-gray-500">{label}</div>
      <div className="mt-1 text-3xl font-semibold text-gray-900">{value}</div>
      {sub ? <div className="mt-1 text-base text-gray-500">{sub}</div> : null}
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
  const [chatOpen, setChatOpen] = useState(true);  // Open by default
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [openMenuId, setOpenMenuId] = useState(null);  // Track which receipt menu is open
  const [lastBudgetContext, setLastBudgetContext] = useState(null);
  const [editingReceipt, setEditingReceipt] = useState(null);  // Receipt being edited
  const [categoryDropdownOpen, setCategoryDropdownOpen] = useState(false);  // For custom dropdown
  const [editCategoryDropdownOpen, setEditCategoryDropdownOpen] = useState(false);  // For edit modal dropdown
  const [chatWidth, setChatWidth] = useState(520);  // Draggable chat width
  const [isResizing, setIsResizing] = useState(false);
  const [hasResized, setHasResized] = useState(false);  // Track if user manually resized

  const CATEGORIES = ["Groceries", "Dining", "Gas", "Shopping", "Entertainment", "Healthcare", "Travel", "Utilities", "Other"];

  // Handle chat panel resize
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing) return;
      const newWidth = window.innerWidth - e.clientX;
      setChatWidth(Math.max(300, Math.min(1000, newWidth)));
      setHasResized(true);
    };
    const handleMouseUp = () => setIsResizing(false);

    if (isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    }
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing]);

// inside your component
const lastBudgetContextRef = useRef(null); // keeps latest budget context instantly

async function handleSendChat() {
  if (!chatInput.trim() || chatLoading) return;

  const userMessage = chatInput.trim();
  setChatInput("");

  // Add user message to chat
  const newMessages = [...chatMessages, { role: "user", content: userMessage }];
  setChatMessages(newMessages);
  setChatLoading(true);

  try {
    // Build conversation history for context
    const history = newMessages.map(m => ({ role: m.role, content: m.content }));

    console.log("Sending budget context:", lastBudgetContextRef.current);

    // Send message to backend with the most up-to-date budget context
    const response = await sendChatMessage(userMessage, history, lastBudgetContextRef.current);

    // Handle response types
    if (response.type === "budget_status" && response.has_budget) {
      // Save context immediately in ref
      lastBudgetContextRef.current = response;
      setLastBudgetContext(response); // also keep state for UI rendering

      setChatMessages(prev => [
        ...newMessages,
        { role: "assistant", content: "budget_status", data: response }
      ]);

    } else if (response.type === "budget_refine") {
      // Update context if backend returns updated budget
      if (response.success && response.data) {
        lastBudgetContextRef.current = response.data;
        setLastBudgetContext(response.data);
      }

      setChatMessages(prev => [
        ...newMessages,
        { role: "assistant", content: "planning", data: response }
      ]);

    } else if (response.type === "planning" || response.type === "planning_refine") {
      setChatMessages(prev => [
        ...newMessages,
        { role: "assistant", content: "planning", data: response }
      ]);

    } else {
      // Default response
      setChatMessages(prev => [
        ...newMessages,
        { role: "assistant", content: response.response || "Sorry, I don't understand." }
      ]);
    }

  } catch (e) {
    setChatMessages(prev => [
      ...newMessages,
      { role: "assistant", content: `Error: ${e.message}` }
    ]);
  } finally {
    setChatLoading(false);
  }
}


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
    <div className="h-screen flex flex-col bg-gray-50 transition-all duration-300" style={{ marginRight: chatOpen && hasResized ? chatWidth : 0 }}>
      {/* Top bar - fixed */}
      <div className="flex-shrink-0 border-b border-gray-200 bg-white/80 backdrop-blur">
        <div className="mx-auto max-w-3xl px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-4xl font-bold text-gray-900">PennyWise</div>
              <div className="text-base text-gray-500">Scan → Save → Trends</div>
            </div>
            <div className="flex gap-2">
              <Pill active={tab === "scan"} onClick={() => setTab("scan")}>Scan</Pill>
              <Pill active={tab === "history"} onClick={() => setTab("history")}>History</Pill>
              <Pill active={tab === "trends"} onClick={() => setTab("trends")}>Trends</Pill>
            </div>
          </div>
        </div>
      </div>

      {/* Main - scrollable */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-6 py-8">
        {err ? (
          <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {err}
          </div>
        ) : null}

        {/* SCAN TAB */}
        {tab === "scan" && (
          <div className="space-y-5">
            <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
              <div className="text-xl font-semibold text-gray-900">1) Capture a receipt</div>
              <div className="mt-3 text-lg text-gray-500">
                Use your phone camera or upload an image. Then hit "Parse".
              </div>

              <div className="mt-5 flex items-center gap-8">
                <label className="rounded-xl border-0 bg-gradient-to-r from-violet-600 to-indigo-600 px-6 py-3.5 text-white font-semibold cursor-pointer transition-all shadow-md hover:from-violet-700 hover:to-indigo-700">
                  Choose File
                  <input
                    type="file"
                    accept="image/*"
                    capture="environment"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                    className="hidden"
                  />
                </label>
                <span className="text-base text-gray-600">
                  {file ? file.name : "no file selected"}
                </span>
              </div>

              <div className="mt-6 flex gap-4">
                <button
                  onClick={onScan}
                  disabled={!file || loading}
                  className={cn(
                    "flex-1 rounded-2xl px-8 py-4 text-lg font-semibold text-white shadow-lg transition-all duration-200",
                    !file || loading
                      ? "bg-gray-300 cursor-not-allowed"
                      : "bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 hover:shadow-xl hover:scale-[1.02]"
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
                  className="rounded-2xl border-2 border-gray-200 bg-white px-8 py-4 text-lg font-semibold text-gray-700 hover:border-gray-300 hover:bg-gray-50 transition-all duration-200"
                  type="button"
                >
                  Reset
                </button>
              </div>
            </div>

            {hasPreview && (
              <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="text-xl font-semibold text-gray-900">2) Preview</div>
                    <div className="mt-3 text-lg text-gray-500">
                      Verify fields before saving.
                    </div>
                  </div>
                  {savedId ? (
                    <span className="rounded-full bg-green-50 px-4 py-2 text-base font-semibold text-green-700 border border-green-200">
                      Saved ✓
                    </span>
                  ) : null}
                </div>

                <div className="mt-5 grid grid-cols-2 gap-4">
                  <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                    <label className="text-base font-medium text-gray-500">Merchant</label>
                    <input
                      type="text"
                      value={preview.merchant || ""}
                      onChange={(e) => setPreview({ ...preview, merchant: e.target.value })}
                      className="mt-1 w-full text-xl font-semibold text-gray-900 bg-transparent border-b border-gray-200 focus:border-violet-500 focus:outline-none"
                    />
                  </div>
                  <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                    <label className="text-base font-medium text-gray-500">Date</label>
                    <input
                      type="text"
                      value={preview.date || ""}
                      onChange={(e) => setPreview({ ...preview, date: e.target.value })}
                      placeholder="YYYY-MM-DD"
                      className="mt-1 w-full text-xl font-semibold text-gray-900 bg-transparent border-b border-gray-200 focus:border-violet-500 focus:outline-none"
                    />
                  </div>
                  <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                    <label className="text-base font-medium text-gray-500">Total</label>
                    <div className="flex items-center mt-1">
                      <span className="text-xl font-semibold text-gray-900">$</span>
                      <input
                        type="text" inputMode="decimal"
                                                value={preview.total || ""}
                        onChange={(e) => setPreview({ ...preview, total: parseFloat(e.target.value) || 0 })}
                        className="w-full text-xl font-semibold text-gray-900 bg-transparent border-b border-gray-200 focus:border-violet-500 focus:outline-none"
                      />
                    </div>
                  </div>
                  <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                    <label className="text-base font-medium text-gray-500">Tax</label>
                    <div className="flex items-center mt-1">
                      <span className="text-xl font-semibold text-gray-900">$</span>
                      <input
                        type="text" inputMode="decimal"
                                                value={preview.tax || ""}
                        onChange={(e) => setPreview({ ...preview, tax: parseFloat(e.target.value) || 0 })}
                        className="w-full text-xl font-semibold text-gray-900 bg-transparent border-b border-gray-200 focus:border-violet-500 focus:outline-none"
                      />
                    </div>
                  </div>
                  <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                    <label className="text-base font-medium text-gray-500">Subtotal</label>
                    <div className="flex items-center mt-1">
                      <span className="text-xl font-semibold text-gray-900">$</span>
                      <input
                        type="text" inputMode="decimal"
                                                value={preview.subtotal || ""}
                        onChange={(e) => setPreview({ ...preview, subtotal: parseFloat(e.target.value) || 0 })}
                        className="w-full text-xl font-semibold text-gray-900 bg-transparent border-b border-gray-200 focus:border-violet-500 focus:outline-none"
                      />
                    </div>
                  </div>
                  <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm relative">
                    <label className="text-base font-medium text-gray-500">Category</label>
                    <button
                      type="button"
                      onClick={() => setCategoryDropdownOpen(!categoryDropdownOpen)}
                      className="mt-1 w-full text-xl font-semibold text-gray-900 bg-transparent border-b border-gray-200 focus:border-violet-500 focus:outline-none text-left flex items-center justify-between py-1"
                    >
                      <span>{preview.category || "Select category"}</span>
                      <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                    {categoryDropdownOpen && (
                      <>
                        <div className="fixed inset-0 z-10" onClick={() => setCategoryDropdownOpen(false)} />
                        <div className="absolute left-0 right-0 bottom-full mb-1 bg-white border border-gray-200 rounded-xl shadow-lg z-20 overflow-hidden max-h-64 overflow-y-auto">
                          {CATEGORIES.map((cat) => (
                            <button
                              key={cat}
                              type="button"
                              onClick={() => {
                                setPreview({ ...preview, category: cat });
                                setCategoryDropdownOpen(false);
                              }}
                              className={cn(
                                "w-full px-4 py-3 text-left text-base hover:bg-violet-50 transition",
                                preview.category === cat ? "bg-violet-100 text-violet-700 font-medium" : "text-gray-700"
                              )}
                            >
                              {cat}
                            </button>
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                </div>

                <div className="mt-5">
                  <div className="text-base font-medium text-gray-500">Items</div>
                  <div className="mt-3 space-y-2">
                    {(preview.items || []).length ? (
                      preview.items.map((it, idx) => (
                        <div
                          key={idx}
                          className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3"
                        >
                          <input
                            type="text"
                            value={it.description || ""}
                            onChange={(e) => {
                              const newItems = [...preview.items];
                              newItems[idx] = { ...newItems[idx], description: e.target.value };
                              setPreview({ ...preview, items: newItems });
                            }}
                            placeholder="Item name"
                            className="flex-1 text-base text-gray-900 bg-transparent focus:outline-none"
                          />
                          <div className="flex items-center text-gray-500">
                            <span>$</span>
                            <input
                              type="text"
                              inputMode="decimal"
                              value={it.total_price || ""}
                              onChange={(e) => {
                                const newItems = [...preview.items];
                                newItems[idx] = { ...newItems[idx], total_price: parseFloat(e.target.value) || 0 };
                                setPreview({ ...preview, items: newItems });
                              }}
                              placeholder="0.00"
                              className="w-16 text-base text-gray-900 bg-transparent focus:outline-none text-right"
                            />
                          </div>
                          <button
                            type="button"
                            onClick={() => {
                              const newItems = preview.items.filter((_, i) => i !== idx);
                              setPreview({ ...preview, items: newItems });
                            }}
                            className="text-gray-300 hover:text-red-500"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      ))
                    ) : (
                      <div className="text-base text-gray-400">No line items detected.</div>
                    )}
                    <button
                      type="button"
                      onClick={() => {
                        const newItems = [...(preview.items || []), { description: "", total_price: 0 }];
                        setPreview({ ...preview, items: newItems });
                      }}
                      className="w-full py-3 rounded-xl border-2 border-dashed border-gray-300 bg-gray-50 text-base font-medium text-gray-500 hover:border-violet-400 hover:bg-violet-50 hover:text-violet-600 transition"
                    >
                      + Add Item
                    </button>
                  </div>
                </div>

                <div className="mt-6">
                  <button
                    onClick={async () => {
                      await onSave();
                      setTab("history");
                    }}
                    disabled={!canSave || loading}
                    className={cn(
                      "w-full rounded-2xl px-6 py-4 text-base font-semibold text-white shadow-lg transition-all duration-200",
                      !canSave || loading
                        ? "bg-gray-300 cursor-not-allowed"
                        : "bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 hover:shadow-xl hover:scale-[1.02]"
                    )}
                    type="button"
                  >
                    {loading ? "Saving..." : "Confirm & Save Receipt"}
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
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <div className="text-xl font-semibold text-gray-900">Receipt History</div>
              <div className="flex gap-3">
                <button
                  onClick={() => refreshReceipts().catch((e) => setErr(e.message))}
                  className="px-4 py-2 text-base font-semibold text-gray-700 bg-gray-100 rounded-xl hover:bg-gray-200 transition-all"
                  type="button"
                >
                  Refresh
                </button>
                <button
                  onClick={() => setReceipts([])}
                  className="px-4 py-2 text-base font-semibold text-red-600 bg-red-50 rounded-xl hover:bg-red-100 transition-all"
                  type="button"
                >
                  Clear
                </button>
              </div>
            </div>

            {receipts.length ? (
              receipts.map((r) => (
                <div key={r.id} className="rounded-2xl border border-gray-200 bg-white shadow-sm relative flex">
                  {/* Main content */}
                  <div className="flex-1 p-6">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="text-lg font-semibold text-gray-900">{r.merchant}</div>
                        <div className="mt-2 text-base text-gray-500">{r.date || "—"} • {r.category}</div>
                      </div>
                      <div className="text-lg font-semibold text-gray-900">
                        <Money v={r.total} />
                      </div>
                    </div>
                    <div className="mt-3 text-base text-gray-500">
                      Tax: <Money v={r.tax} /> • Saved: {r.created_at || "—"}
                    </div>
                  </div>
                  {/* Three-dot menu - full height */}
                  <div className="relative border-l border-gray-100">
                    <button
                      onClick={() => setOpenMenuId(openMenuId === r.id ? null : r.id)}
                      className="h-full px-4 hover:bg-gray-50 transition flex items-center justify-center rounded-r-2xl"
                      type="button"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                      </svg>
                    </button>
                    {/* Dropdown menu */}
                    {openMenuId === r.id && (
                      <>
                      <div className="fixed inset-0 z-10" onClick={() => setOpenMenuId(null)} />
                      <div className="absolute left-full top-1/2 -translate-y-1/2 ml-2 w-32 bg-white border border-gray-200 rounded-xl shadow-lg z-[60] overflow-hidden">
                        <button
                          onClick={() => {
                            setEditingReceipt({ ...r });
                            setOpenMenuId(null);
                          }}
                          className="w-full px-4 py-3 text-left text-base text-gray-700 hover:bg-gray-50"
                          type="button"
                        >
                          Edit
                        </button>
                        <button
                          onClick={async () => {
                            try {
                              await deleteReceipt(r.id);
                              setReceipts(receipts.filter(rec => rec.id !== r.id));
                              setOpenMenuId(null);
                            } catch (e) {
                              setErr(e.message);
                            }
                          }}
                          className="w-full px-4 py-3 text-left text-base text-red-600 hover:bg-red-50"
                          type="button"
                        >
                          Delete
                        </button>
                      </div>
                      </>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-gray-200 bg-white p-6 text-lg text-gray-500 shadow-sm">
                No receipts yet. Go to Scan and save one.
              </div>
            )}
          </div>
        )}

        {/* INSIGHTS TAB */}
        {tab === "insights" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-lg font-semibold text-gray-900">Weekly Insights</div>
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
                  <div className="text-lg font-semibold text-gray-900">Spend by category</div>
                  <div className="mt-3 space-y-2">
                    {Object.entries(insights.spend_by_category || {}).map(([k, v]) => (
                      <div key={k} className="flex items-center justify-between">
                        <div className="text-sm text-gray-700">{k}</div>
                        <div className="text-lg font-semibold text-gray-900">
                          ${Number(v).toFixed(2)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
                  <div className="text-xl font-semibold text-gray-900">Story</div>
                  <ul className="mt-3 list-disc space-y-2 pl-5 text-base text-gray-700">
                    {(insights.story_insights || []).map((s, i) => <li key={i}>{s}</li>)}
                  </ul>
                  <div className="mt-4 rounded-xl bg-gray-50 p-4 text-base font-medium text-gray-900">
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
          <div className="space-y-5">
            {/* Period Toggle - Apple Health Style */}
            <div className="flex justify-center">
              <div className="inline-flex rounded-xl bg-gray-100 p-1.5 flex-wrap gap-1">
                {["custom", "daily", "weekly", "monthly", "yearly", "all"].map((p) => (
                  <button
                    key={p}
                    onClick={() => setTrendsPeriod(p)}
                    className={cn(
                      "px-4 py-2.5 rounded-lg text-base font-medium transition",
                      trendsPeriod === p
                        ? "bg-white text-gray-900 shadow"
                        : "text-gray-600 hover:text-gray-900"
                    )}
                    type="button"
                  >
                    {p === "all" ? "All Time" : p === "custom" ? "Custom" : p.charAt(0).toUpperCase() + p.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {/* Custom Date Range */}
            {trendsPeriod === "custom" && (
              <div className="flex items-center gap-3 justify-center flex-wrap">
                <input
                  type="date"
                  value={customStartDate}
                  onChange={(e) => setCustomStartDate(e.target.value)}
                  className="rounded-xl border border-gray-200 px-3 py-2 text-base"
                />
                <span className="text-gray-400">to</span>
                <input
                  type="date"
                  value={customEndDate}
                  onChange={(e) => setCustomEndDate(e.target.value)}
                  className="rounded-xl border border-gray-200 px-3 py-2 text-base"
                />
                <button
                  onClick={() => {
                    refreshTrends("custom", customStartDate, customEndDate).catch((e) => setErr(e.message));
                    refreshChartsData("custom").catch((e) => setErr(e.message));
                  }}
                  disabled={!customStartDate || !customEndDate}
                  className={cn(
                    "px-5 py-2 rounded-xl text-base font-semibold transition-all",
                    customStartDate && customEndDate
                      ? "bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:from-violet-700 hover:to-indigo-700 shadow-md"
                      : "bg-gray-200 text-gray-400"
                  )}
                  type="button"
                >
                  Apply
                </button>
              </div>
            )}

            {/* If custom selected but no dates, prompt user */}
            {trendsPeriod === "custom" && (!customStartDate || !customEndDate) ? (
              <div className="rounded-2xl border border-gray-200 bg-white p-8 text-center shadow-sm">
                <div className="text-5xl mb-3">📅</div>
                <div className="text-lg font-medium text-gray-700">Select a date range</div>
                <div className="text-base text-gray-400 mt-1">Choose start and end dates above to see your spending trends</div>
              </div>
            ) : trends ? (
              <div className="space-y-4">
                {/* Summary Stats */}
                <div className="grid grid-cols-2 gap-3">
                  <StatCard
                    label="Total Spending"
                    value={`$${Number(trends.total_spend).toFixed(2)}`}
                  />
                  <StatCard
                    label="Receipts"
                    value={trends.receipt_count}
                  />
                </div>

                {/* Comparison Card - hide for custom date range */}
                {trends.comparison && trendsPeriod !== "custom" && (
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
                        <div className="text-lg font-semibold text-gray-900">
                          {trends.comparison.message}
                        </div>
                        <div className="text-base text-gray-500">
                          {trends.period_start} to {trends.period_end}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Pie Chart */}
                {Object.keys(trends.spend_by_category || {}).length > 0 ? (
                  <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                    <div className="text-lg font-semibold text-gray-900 mb-4">
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
                          <span className="text-lg font-semibold text-gray-900">
                            ${Number(amount).toFixed(2)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-gray-200 bg-white p-6 text-center shadow-sm">
                    <div className="text-5xl mb-3">📊</div>
                    <div className="text-lg text-gray-500">
                      No spending data for this period.
                    </div>
                    <div className="text-base text-gray-400 mt-2">
                      Add some receipts to see your trends!
                    </div>
                  </div>
                )}

                {/* Spending Over Time Chart */}
                {chartsData?.spending_over_time?.length > 0 && (
                  <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                    <div className="text-lg font-semibold text-gray-900 mb-4">
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
                    <div className="text-lg font-semibold text-gray-900 mb-4">
                      Top Merchants
                    </div>
                    <ResponsiveContainer width="100%" height={Math.max(200, chartsData.top_merchants.length * 40)}>
                      <BarChart data={chartsData.top_merchants} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis type="text" inputMode="decimal" tick={{ fontSize: 12 }} tickFormatter={(v) => `$${v}`} />
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
                    <div className="text-lg font-semibold text-gray-900 mb-4">
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
                            <span className="text-sm text-gray-600">{cat}</span>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                {/* Day of Week Chart */}
                {chartsData?.day_of_week?.length > 0 && (
                  <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                    <div className="text-lg font-semibold text-gray-900 mb-4">
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
                  <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
                    <div className="text-xl font-semibold text-gray-900">Story</div>
                    <ul className="mt-3 list-disc space-y-2 pl-5 text-base text-gray-700">
                      {(insights.story_insights || []).map((s, i) => <li key={i}>{s}</li>)}
                    </ul>
                    <div className="mt-4 rounded-xl bg-gray-50 p-4 text-base font-medium text-gray-900">
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

      {/* Edit Receipt Modal */}
      {editingReceipt && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-2xl overflow-visible">
            <div className="text-xl font-semibold text-gray-900 mb-4">Edit Receipt</div>

            <div className="space-y-4 overflow-visible">
              <div>
                <label className="text-base font-medium text-gray-500">Merchant</label>
                <input
                  type="text"
                  value={editingReceipt.merchant || ""}
                  onChange={(e) => setEditingReceipt({ ...editingReceipt, merchant: e.target.value })}
                  className="mt-1 w-full rounded-xl border-2 border-gray-200 px-4 py-3 text-base focus:outline-none focus:border-violet-500"
                />
              </div>
              <div>
                <label className="text-base font-medium text-gray-500">Date</label>
                <input
                  type="text"
                  value={editingReceipt.date || ""}
                  onChange={(e) => setEditingReceipt({ ...editingReceipt, date: e.target.value })}
                  placeholder="YYYY-MM-DD"
                  className="mt-1 w-full rounded-xl border-2 border-gray-200 px-4 py-3 text-base focus:outline-none focus:border-violet-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-base font-medium text-gray-500">Total</label>
                  <input
                    type="text" inputMode="decimal"
                                        value={editingReceipt.total || ""}
                    onChange={(e) => setEditingReceipt({ ...editingReceipt, total: parseFloat(e.target.value) || 0 })}
                    className="mt-1 w-full rounded-xl border-2 border-gray-200 px-4 py-3 text-base focus:outline-none focus:border-violet-500"
                  />
                </div>
                <div>
                  <label className="text-base font-medium text-gray-500">Tax</label>
                  <input
                    type="text" inputMode="decimal"
                                        value={editingReceipt.tax || ""}
                    onChange={(e) => setEditingReceipt({ ...editingReceipt, tax: parseFloat(e.target.value) || 0 })}
                    className="mt-1 w-full rounded-xl border-2 border-gray-200 px-4 py-3 text-base focus:outline-none focus:border-violet-500"
                  />
                </div>
              </div>
              <div className="overflow-visible">
                <label className="text-base font-medium text-gray-500">Category</label>
                <button
                  type="button"
                  onClick={() => setEditCategoryDropdownOpen(!editCategoryDropdownOpen)}
                  className="mt-1 w-full rounded-xl border-2 border-gray-200 px-4 py-3 text-base focus:outline-none focus:border-violet-500 text-left flex items-center justify-between bg-white overflow-visible"
                >
                  <span className={editingReceipt.category ? "text-gray-900" : "text-gray-400"}>
                    {editingReceipt.category || "Select category"}
                  </span>
                  <div className="relative">
                    <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                    {editCategoryDropdownOpen && (
                      <div className="absolute left-full top-1/2 -translate-y-1/2 ml-4 bg-white border border-gray-200 rounded-xl shadow-lg z-[100] max-h-64 overflow-y-auto w-40">
                        {CATEGORIES.map((cat) => (
                          <button
                            key={cat}
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditingReceipt({ ...editingReceipt, category: cat });
                              setEditCategoryDropdownOpen(false);
                            }}
                            className={cn(
                              "w-full px-4 py-3 text-left text-base hover:bg-violet-50 transition",
                              editingReceipt.category === cat ? "bg-violet-100 text-violet-700 font-medium" : "text-gray-700"
                            )}
                          >
                            {cat}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </button>
                {editCategoryDropdownOpen && (
                  <div className="fixed inset-0 z-[99]" onClick={() => setEditCategoryDropdownOpen(false)} />
                )}
              </div>
            </div>

            <div className="mt-6 flex gap-3">
              <button
                onClick={async () => {
                  try {
                    await updateReceipt(editingReceipt.id, {
                      merchant: editingReceipt.merchant,
                      date: editingReceipt.date,
                      total: editingReceipt.total,
                      tax: editingReceipt.tax,
                      category: editingReceipt.category,
                    });
                    setReceipts(receipts.map(r => r.id === editingReceipt.id ? editingReceipt : r));
                    setEditingReceipt(null);
                  } catch (e) {
                    setErr(e.message);
                  }
                }}
                className="flex-1 rounded-xl px-6 py-3 text-base font-semibold text-white bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 transition-all shadow-md"
                type="button"
              >
                Save Changes
              </button>
              <button
                onClick={() => setEditingReceipt(null)}
                className="rounded-xl px-6 py-3 text-base font-semibold text-gray-700 border-2 border-gray-200 hover:bg-gray-50 transition-all"
                type="button"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Chat Panel - slides in from right */}
      <div
        className={cn(
          "fixed top-0 right-0 h-full bg-white border-l border-gray-200 shadow-xl transition-transform duration-300 z-50 flex flex-col",
          chatOpen ? "translate-x-0" : "translate-x-full"
        )}
        style={{ width: chatWidth }}
      >
        {/* Drag handle */}
        <div
          className="absolute left-0 top-0 bottom-0 w-2 cursor-ew-resize hover:bg-violet-400 active:bg-violet-500 transition-colors z-10"
          onMouseDown={() => setIsResizing(true)}
        />
        {/* Chat Header with close arrow */}
        <div className="flex items-center justify-between p-5 border-b border-gray-200">
          <div className="text-xl font-semibold text-gray-900">Chat Assistant</div>
          <button
            onClick={() => setChatOpen(false)}
            className="p-1 hover:bg-gray-100 rounded-lg transition"
            type="button"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>

  {/* Chat Messages */}
  <div className="flex-1 overflow-y-auto p-4 space-y-3">
    {chatMessages.length === 0 ? (
      <div className="text-center text-gray-400 text-lg mt-8">
        Ask me anything about your spending!
      </div>
    ) : (
      chatMessages.map((msg, idx) => {
        if (msg.role === "assistant" && msg.content === "budget_status") {
          const budget = msg.data;
          return (
            <div key={idx} className="p-4 rounded-xl bg-gray-100 text-gray-900 max-w-[90%]">
              <div className="text-lg font-semibold mb-2">Budget Summary ({budget.plan.period})</div>
              <div className="text-sm text-gray-700 mb-2">
                Overall: ${budget.status.overall.budgeted} budgeted, ${budget.status.overall.actual} spent, ${budget.status.overall.remaining} remaining
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                {Object.entries(budget.status.by_category).map(([cat, val]) => (
                  <div key={cat} className="p-2 border rounded-lg bg-white">
                    <div className="font-medium">{cat}</div>
                    <div>Budgeted: ${val.budgeted}</div>
                    <div>Actual: ${val.actual}</div>
                    <div>Remaining: ${val.remaining}</div>
                  </div>
                ))}
              </div>
            </div>
          );
        }

        // Default message
        return (
          <div
            key={idx}
            className={cn(
              "p-3 rounded-xl text-base max-w-[85%]",
              msg.role === "user"
                ? "bg-gradient-to-r from-violet-600 to-indigo-600 text-white ml-auto"
                : "bg-gray-100 text-gray-900"
            )}
          >
            {typeof msg.content === "string" ? msg.content : JSON.stringify(msg.content)}
        {/* Chat Input */}
        <div className="p-5 border-t border-gray-200">
          <div className="flex gap-3">
            <textarea
              value={chatInput}
              onChange={(e) => {
                setChatInput(e.target.value);
                e.target.style.height = "auto";
                e.target.style.height = Math.min(e.target.scrollHeight, 150) + "px";
              }}
              placeholder="Type a message..."
              className="flex-1 rounded-2xl border-2 border-gray-200 px-5 py-4 text-base focus:outline-none focus:border-violet-400 resize-none overflow-hidden"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSendChat();
                }
              }}
              disabled={chatLoading}
              rows={1}
              style={{ minHeight: "56px", maxHeight: "150px" }}
            />
            <button
              onClick={handleSendChat}
              disabled={chatLoading}
              className={cn(
                "px-6 py-4 rounded-2xl text-base font-semibold transition-all shadow-md",
                chatLoading
                  ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                  : "bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:from-violet-700 hover:to-indigo-700"
              )}
              type="button"
            >
              {chatLoading ? "..." : "Send"}
            </button>
          </div>
        );
      })
    )}
  </div>

  {/* Chat Input */}
  <div className="p-5 border-t border-gray-200">
    <div className="flex gap-3">
      <input
        type="text"
        value={chatInput}
        onChange={(e) => setChatInput(e.target.value)}
        placeholder="Type a message..."
        className="flex-1 rounded-2xl border-2 border-gray-200 px-5 py-4 text-base focus:outline-none focus:border-violet-400"
        onKeyDown={(e) => {
          if (e.key === "Enter") handleSendChat();
        }}
        disabled={chatLoading}
      />
      <button
        onClick={handleSendChat}
        disabled={chatLoading || !chatInput.trim()}
        className={cn(
          "px-6 py-4 rounded-2xl text-base font-semibold transition-all shadow-md",
          chatLoading || !chatInput.trim()
            ? "bg-gray-300 text-gray-500 cursor-not-allowed"
            : "bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:from-violet-700 hover:to-indigo-700"
        )}
        type="button"
      >
        {chatLoading ? "..." : "Send"}
      </button>
    </div>
  </div>
</div>

      {/* Button to reopen chat when closed */}
      {!chatOpen && (
        <button
          onClick={() => setChatOpen(true)}
          className="fixed bottom-8 right-8 p-5 bg-gradient-to-r from-violet-600 to-indigo-600 text-white rounded-full shadow-xl hover:from-violet-700 hover:to-indigo-700 hover:shadow-2xl hover:scale-105 transition-all z-50"
          type="button"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        </button>
      )}
    </div>
  );
}
