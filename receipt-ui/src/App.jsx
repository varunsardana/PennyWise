import { useEffect, useMemo, useState } from "react";
import {
  parseReceipt,
  saveReceipt,
  listReceipts,
  getInsights,
  getTrends,
  getChartsData,
  getForecast,
  deleteReceipt,
  sendChatMessage,
} from "./api";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  LineChart,
  Line,
} from "recharts";

const CATEGORIES = [
  "Groceries",
  "Dining",
  "Transportation",
  "Entertainment",
  "Shopping",
  "Health",
  "Utilities",
  "Other"
];

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

// Left Dashboard - unified panel with tips and stats
function LeftDashboard({ receipts }) {
  const tips = [
    { icon: "💡", title: "50/30/20 Rule", text: "Spend 50% on needs, 30% on wants, 20% on savings" },
    { icon: "🎯", title: "Track Everything", text: "Small purchases add up - track every receipt!" },
    { icon: "☕", title: "Latte Factor", text: "That $5 daily coffee = $1,825/year. Small changes matter!" },
    { icon: "🏦", title: "Pay Yourself First", text: "Save before you spend, not after" },
    { icon: "📊", title: "Review Weekly", text: "Check your spending every week to stay on track" },
    { icon: "🛒", title: "List Before Shopping", text: "Make a list and stick to it - avoid impulse buys" },
    { icon: "💳", title: "Wait 24 Hours", text: "Sleep on big purchases to avoid buyer's remorse" },
    { icon: "🎁", title: "Reward Yourself", text: "Budget for fun too - sustainable saving needs balance" },
  ];

  const [currentTip, setCurrentTip] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTip((prev) => (prev + 1) % tips.length);
    }, 6000);
    return () => clearInterval(interval);
  }, []);

  const tip = tips[currentTip];

  const stats = useMemo(() => {
    if (!receipts || receipts.length === 0) return null;

    const total = receipts.reduce((sum, r) => sum + (r.total || 0), 0);
    const avg = total / receipts.length;

    const categoryCount = {};
    receipts.forEach(r => {
      if (r.category) {
        categoryCount[r.category] = (categoryCount[r.category] || 0) + 1;
      }
    });
    const topCategory = Object.entries(categoryCount).sort((a, b) => b[1] - a[1])[0];
    const categoryCountNum = Object.keys(categoryCount).length;

    const now = new Date();
    const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    const thisWeek = receipts.filter(r => {
      if (!r.date) return false;
      const d = new Date(r.date);
      return d >= weekAgo;
    });
    const weekTotal = thisWeek.reduce((sum, r) => sum + (r.total || 0), 0);

    return { total, avg, count: receipts.length, topCategory: topCategory ? topCategory[0] : 'N/A', weekTotal, categoryCountNum };
  }, [receipts]);

  // Achievement badges - reward good tracking habits, not spending!
  const badges = useMemo(() => {
    const count = stats?.count || 0;
    const categories = stats?.categoryCountNum || 0;

    return [
      { id: 1, icon: "🎯", name: "First Penny", requirement: "Track 1 receipt", unlocked: count >= 1 },
      { id: 2, icon: "📝", name: "Getting Started", requirement: "Track 5 receipts", unlocked: count >= 5 },
      { id: 3, icon: "🔥", name: "On Fire", requirement: "Track 10 receipts", unlocked: count >= 10 },
      { id: 4, icon: "⭐", name: "Dedicated", requirement: "Track 25 receipts", unlocked: count >= 25 },
      { id: 5, icon: "👑", name: "Tracking Pro", requirement: "Track 50 receipts", unlocked: count >= 50 },
      { id: 6, icon: "🌈", name: "Explorer", requirement: "Use 3+ categories", unlocked: categories >= 3 },
      { id: 7, icon: "🏆", name: "Organizer", requirement: "Use 5+ categories", unlocked: categories >= 5 },
      { id: 8, icon: "💰", name: "Budget Boss", requirement: "Stay under budget", unlocked: false }, // Coming soon with budgets!
    ];
  }, [stats]);

  return (
    <div className="fixed bottom-4 left-4 w-[420px] z-[100] space-y-3">
      {/* Achievement Badges - TOP */}
      <div className="bg-white/95 backdrop-blur rounded-2xl shadow-lg border border-gray-100 p-6">
        <div className="text-base font-semibold text-gray-400 uppercase tracking-wide mb-5">Achievements</div>
        <div className="grid grid-cols-4 gap-4">
          {badges.map((badge) => (
            <div
              key={badge.id}
              className="relative group cursor-pointer p-2 rounded-xl"
            >
              <div className={cn(!badge.unlocked && "opacity-40 grayscale")}>
                <div className={cn(
                  "w-16 h-16 rounded-xl flex items-center justify-center text-3xl transition-transform group-hover:scale-110 mx-auto",
                  badge.unlocked
                    ? "bg-gradient-to-br from-amber-400 to-orange-500 shadow-md"
                    : "bg-gray-200"
                )}>
                  {badge.icon}
                </div>
                <div className="text-xs text-center mt-2 font-medium text-gray-600 truncate">
                  {badge.name}
                </div>
              </div>
              {badge.unlocked && (
                <div className="absolute top-1 right-1 w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs">✓</span>
                </div>
              )}
              {/* Hover popup */}
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-4 py-3 bg-gray-900 text-white text-sm rounded-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50 shadow-xl">
                <div className="font-bold text-base">{badge.name}</div>
                <div className="text-white mt-1">{badge.requirement}</div>
                <div className="absolute top-full left-1/2 -translate-x-1/2 border-[6px] border-transparent border-t-gray-900"></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Tips Card */}
      <div className="bg-gradient-to-br from-violet-500 to-indigo-600 rounded-2xl shadow-lg p-6 text-white h-[160px] flex flex-col">
        <div className="flex items-start gap-4 flex-1">
          <div className="text-4xl">{tip.icon}</div>
          <div className="flex-1">
            <div className="font-bold text-lg">{tip.title}</div>
            <div className="text-violet-100 text-base mt-1 leading-relaxed">{tip.text}</div>
          </div>
        </div>
        <div className="flex justify-center gap-2 mt-auto pt-3">
          {tips.map((_, i) => (
            <button
              key={i}
              onClick={() => setCurrentTip(i)}
              className={cn(
                "h-2 rounded-full transition-all",
                i === currentTip ? "bg-white w-5" : "bg-white/40 w-2"
              )}
            />
          ))}
        </div>
      </div>

      {/* Stats Card */}
      <div className="bg-white/95 backdrop-blur rounded-2xl shadow-lg border border-gray-100 p-6">
        <div className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-4">Your Stats</div>
        {stats ? (
          <div className="grid grid-cols-2 gap-5">
            <div>
              <div className="text-3xl font-bold text-violet-600">${stats.weekTotal.toFixed(0)}</div>
              <div className="text-sm text-gray-500">This Week</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-gray-800">{stats.count}</div>
              <div className="text-sm text-gray-500">Receipts</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-gray-800">${stats.avg.toFixed(0)}</div>
              <div className="text-sm text-gray-500">Average</div>
            </div>
            <div>
              <div className="text-xl font-bold text-emerald-600">{stats.topCategory}</div>
              <div className="text-sm text-gray-500">Top Category</div>
            </div>
          </div>
        ) : (
          <div className="text-center py-4">
            <div className="text-gray-400 text-base">No receipts yet</div>
            <div className="text-gray-500 text-sm mt-1">Scan your first receipt!</div>
          </div>
        )}
      </div>
    </div>
  );
}

// Cute piggy bank SVG - front view
function PiggyBank({ size = 120 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Body */}
      <circle cx="50" cy="50" r="40" fill="#F8BBD9"/>
      {/* Left ear */}
      <ellipse cx="20" cy="18" rx="10" ry="14" fill="#F8BBD9"/>
      <ellipse cx="20" cy="18" rx="6" ry="8" fill="#E891AB"/>
      {/* Right ear */}
      <ellipse cx="80" cy="18" rx="10" ry="14" fill="#F8BBD9"/>
      <ellipse cx="80" cy="18" rx="6" ry="8" fill="#E891AB"/>
      {/* Left eye */}
      <circle cx="35" cy="42" r="10" fill="white"/>
      <circle cx="37" cy="43" r="6" fill="#333"/>
      <circle cx="39" cy="41" r="2.5" fill="white"/>
      {/* Right eye */}
      <circle cx="65" cy="42" r="10" fill="white"/>
      <circle cx="67" cy="43" r="6" fill="#333"/>
      <circle cx="69" cy="41" r="2.5" fill="white"/>
      {/* Snout */}
      <ellipse cx="50" cy="62" rx="16" ry="12" fill="#E891AB"/>
      {/* Nostrils */}
      <ellipse cx="44" cy="62" rx="3.5" ry="5" fill="#C97087"/>
      <ellipse cx="56" cy="62" rx="3.5" ry="5" fill="#C97087"/>
      {/* Legs */}
      <ellipse cx="35" cy="88" rx="8" ry="10" fill="#F8BBD9"/>
      <ellipse cx="65" cy="88" rx="8" ry="10" fill="#F8BBD9"/>
    </svg>
  );
}

// Chaotic penny rain - coins fall and stay where they land
function FallingCoins({ show, onComplete }) {
  const [coins, setCoins] = useState([]);

  useEffect(() => {
    if (!show) return;

    const numCoins = 80;
    const allCoins = [];

    for (let i = 0; i < numCoins; i++) {
      const finalLeftPx = 220 + Math.random() * 180; // Next to pig (220-400px from left)
      const finalBottomPx = 5 + Math.random() * 55;

      allCoins.push({
        id: i,
        finalLeftPx,
        finalBottomPx,
        delay: Math.random() * 5,
        duration: 2.5 + Math.random() * 1.5, // 2.5-4s fall
        size: 26 + Math.random() * 6,
        spinSpeed: 0.5 + Math.random() * 0.3,
        tiltX: 55 + Math.random() * 25,
        tiltZ: Math.random() * 50 - 25,
        zIndex: Math.floor(Math.random() * 50),
        spinStart: Math.random() * 360,
      });
    }

    setCoins(allCoins);

    const doneTimer = setTimeout(() => {
      onComplete?.();
    }, 10000);

    return () => clearTimeout(doneTimer);
  }, [show]);

  if (!coins.length) return null;

  return (
    <div className="fixed inset-0 pointer-events-none z-[200] overflow-hidden">
      {/* Piggy bank in corner */}
      <div className="fixed bottom-2 left-4 z-[201]">
        <PiggyBank size={160} />
      </div>

      {coins.map((coin) => {
        const spinIterations = Math.ceil(coin.duration / coin.spinSpeed);
        return (
          <div
            key={coin.id}
            className="absolute will-change-transform"
            style={{
              left: coin.finalLeftPx,
              bottom: coin.finalBottomPx,
              zIndex: coin.zIndex,
              animation: `fall ${coin.duration}s linear ${coin.delay}s both`,
            }}
          >
            <div
              style={{
                animation: `spin-${coin.id} ${coin.spinSpeed}s linear ${coin.delay}s ${spinIterations}`,
              }}
            >
              <Penny3D size={coin.size} tiltX={coin.tiltX} tiltZ={coin.tiltZ} />
            </div>
          </div>
        );
      })}

      <style>{`
        @keyframes fall {
          0% { transform: translateY(calc(-100vh - 150px)); }
          100% { transform: translateY(0); }
        }
        ${coins.map(coin => `
          @keyframes spin-${coin.id} {
            0% { transform: rotateX(${coin.spinStart}deg) rotateY(0deg); }
            100% { transform: rotateX(${coin.spinStart + 720}deg) rotateY(360deg); }
          }
        `).join('\n')}
      `}</style>
    </div>
  );
}

// 3D Penny component - shiny copper with warmth
function Penny3D({ size, tiltX = 65, tiltZ = 0 }) {
  const thickness = 8;

  return (
    <div
      className="relative"
      style={{
        width: size,
        height: size,
        transformStyle: "preserve-3d",
        transform: `rotateX(${tiltX}deg) rotateZ(${tiltZ}deg)`,
      }}
    >
      {/* Top face - warm copper with shine */}
      <div
        className="absolute inset-0 rounded-full"
        style={{
          background: `
            radial-gradient(ellipse at 25% 25%, rgba(255,255,255,0.9) 0%, transparent 18%),
            radial-gradient(ellipse at 35% 35%, #e8c39e 0%, transparent 35%),
            radial-gradient(ellipse at 70% 70%, #8b4513 0%, transparent 45%),
            linear-gradient(135deg, #cd7f32 0%, #b87333 25%, #a0522d 50%, #b87333 75%, #cd7f32 100%)
          `,
          boxShadow: `
            inset 0 3px 8px rgba(255,220,180,0.7),
            inset 0 -2px 6px rgba(101,67,33,0.5),
            0 3px 10px rgba(0,0,0,0.35)
          `,
          border: "1.5px solid #8b4513",
          transform: `translateZ(${thickness / 2}px)`,
        }}
      >
        {/* Inner rim */}
        <div
          className="absolute rounded-full border border-amber-800/40"
          style={{ inset: 2 }}
        />
        {/* Cent symbol */}
        <div
          className="absolute inset-0 flex items-center justify-center font-bold"
          style={{
            fontSize: size * 0.4,
            color: "#5c3317",
            textShadow: "0 1px 2px rgba(255,200,150,0.5)",
          }}
        >
          ¢
        </div>
        {/* Shine highlight */}
        <div
          className="absolute inset-0 rounded-full"
          style={{
            background: `
              linear-gradient(110deg, rgba(255,255,255,0.8) 0%, rgba(255,255,255,0.4) 12%, transparent 35%),
              linear-gradient(280deg, rgba(255,200,150,0.3) 0%, transparent 20%)
            `,
          }}
        />
      </div>

      {/* Bottom face */}
      <div
        className="absolute rounded-full"
        style={{
          width: size,
          height: size,
          background: "linear-gradient(to bottom, #8b4513 0%, #6b3a1a 50%, #4a2810 100%)",
          transform: `translateZ(${-thickness / 2}px)`,
          boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
        }}
      />

      {/* Side edge - warm copper */}
      {Array.from({ length: thickness }).map((_, i) => (
        <div
          key={i}
          className="absolute rounded-full"
          style={{
            width: size,
            height: size,
            background: `linear-gradient(to right,
              #6b3a1a 0%,
              #b87333 15%,
              #cd7f32 30%,
              #b87333 50%,
              #8b4513 70%,
              #b87333 85%,
              #6b3a1a 100%
            )`,
            transform: `translateZ(${thickness / 2 - i}px)`,
          }}
        />
      ))}
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState("scan");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [preview, setPreview] = useState(null);
  const [savedId, setSavedId] = useState(null);
  const [receipts, setReceipts] = useState([]);
  const [insights, setInsights] = useState(null);
  const [trends, setTrends] = useState(null);
  const [chartsData, setChartsData] = useState(null);
  const [forecastData, setForecastData] = useState(null);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [trendsPeriod, setTrendsPeriod] = useState("weekly");
  const [customStartDate, setCustomStartDate] = useState("");
  const [customEndDate, setCustomEndDate] = useState("");
  const [chatOpen, setChatOpen] = useState(true);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [openMenuId, setOpenMenuId] = useState(null);
  const [categoryDropdownOpen, setCategoryDropdownOpen] = useState(false);
  const [editingReceipt, setEditingReceipt] = useState(null);
  const [chatWidth, setChatWidth] = useState(400);
  const [isResizing, setIsResizing] = useState(false);
  const [hasResized, setHasResized] = useState(false);  // Track if user manually resized
  const [showCoins, setShowCoins] = useState(false);  // Disabled for now

  const CATEGORIES = ["Groceries", "Dining", "Gas", "Shopping", "Entertainment", "Healthcare", "Travel", "Utilities", "Other"];

  const COLORS = [
    "#8b5cf6",
    "#06b6d4",
    "#10b981",
    "#f59e0b",
    "#ef4444",
    "#ec4899",
    "#6366f1",
    "#84cc16",
  ];

  const hasPreview = !!preview;

  async function handleSendChat() {
    if (!chatInput.trim() || chatLoading) return;

    const userMessage = chatInput.trim();
    setChatInput("");

    const newMessages = [...chatMessages, { role: "user", content: userMessage }];
    setChatMessages(newMessages);
    setChatLoading(true);

    try {
      const history = newMessages.map((m) => ({ role: m.role, content: m.content }));
      const response = await sendChatMessage(userMessage, history);
      setChatMessages([...newMessages, { role: "assistant", content: response.response }]);
    } catch (e) {
      setChatMessages([
        ...newMessages,
        { role: "assistant", content: "Sorry, I encountered an error. Please try again." },
      ]);
    } finally {
      setChatLoading(false);
    }
  }

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

  // Load receipts on startup for the stats dashboard
  useEffect(() => {
    refreshReceipts().catch(() => {});
  }, []);
  async function refreshForecast(horizon = 12) {
    setForecastLoading(true);
    try {
      const data = await getForecast(horizon);
      setForecastData(data);
    } catch (e) {
      setErr(e.message);
    } finally {
      setForecastLoading(false);
    }
  }

  useEffect(() => {
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

  useEffect(() => {
    if (tab === "trends") {
      refreshTrends(trendsPeriod).catch((e) => setErr(e.message));
      refreshChartsData(trendsPeriod).catch((e) => setErr(e.message));
    }
  }, [trendsPeriod, tab]);

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (isResizing) {
        const newWidth = window.innerWidth - e.clientX;
        if (newWidth >= 300 && newWidth <= 800) {
          setChatWidth(newWidth);
          setHasResized(true);
        }
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing]);

  const canSave = useMemo(() => {
    if (!preview) return false;
    return !!preview.merchant && (preview.total ?? 0) > 0 && !!preview.category;
  }, [preview]);

  const forecastTimeline = useMemo(() => {
    if (!forecastData) return [];

    const hist = (forecastData.history || []).map((r) => ({
      week: r.week,
      history: Number(r.total || 0),
      baseline: null,
      improved: null,
    }));

    const fut = (forecastData.baseline || []).map((r, i) => ({
      week: r.week,
      history: null,
      baseline: Number(r.total || 0),
      improved: Number(forecastData.improved?.[i]?.total ?? null),
    }));

    return [...hist, ...fut];
  }, [forecastData]);

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
    <>
    {/* Falling coins animation on load */}
    <FallingCoins show={showCoins} onComplete={() => setShowCoins(false)} />
    <LeftDashboard receipts={receipts} />

    <div className="h-screen flex flex-col bg-gray-50 transition-all duration-300" style={{ marginRight: chatOpen && hasResized ? chatWidth : 0 }}>
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

      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-6 py-8">
          {err ? (
            <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {err}
            </div>
          ) : null}

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
                          type="text" 
                          inputMode="decimal"
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
                          type="text" 
                          inputMode="decimal"
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
                          type="text" 
                          inputMode="decimal"
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

          {tab === "trends" && (
            <div className="space-y-5">
              <div className="flex justify-center">
                <div className="inline-flex rounded-xl bg-gray-100 p-1.5 flex-wrap gap-1">
                  {["daily", "weekly", "monthly", "yearly", "all"].map((p) => (
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
                      {p === "all" ? "All Time" : p.charAt(0).toUpperCase() + p.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              {trends ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <StatCard
                      label="Total Spend"
                      value={`${Number(trends.total_spend).toFixed(2)}`}
                    />
                    <StatCard label="Receipts" value={trends.receipt_count} />
                  </div>

                  <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <div className="text-lg font-semibold text-gray-900">
                          Future Spend Forecast
                        </div>
                        <div className="text-sm text-gray-500">
                          Baseline = keep habits. Improved = follow plan.
                        </div>
                      </div>

                      <button
                        onClick={() => refreshForecast(12)}
                        disabled={forecastLoading}
                        className={cn(
                          "px-4 py-2 rounded-xl text-base font-semibold transition-all",
                          forecastLoading
                            ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                            : "bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:from-violet-700 hover:to-indigo-700 shadow"
                        )}
                        type="button"
                      >
                        {forecastLoading ? "Generating..." : "Generate Forecast"}
                      </button>
                    </div>

                    {forecastData?.summary ? (
                      <div className="mt-4 grid grid-cols-2 gap-3">
                        <StatCard
                          label="Estimated savings"
                          value={`${Number(forecastData.summary.savings).toFixed(2)}`}
                          sub={
                            forecastData?.plan
                              ? `Cut ${forecastData.plan.top_category} by ${forecastData.plan.reduction_percent}%`
                              : null
                          }
                        />
                        <StatCard
                          label="Next 12 weeks total"
                          value={`${Number(forecastData.summary.improved_total).toFixed(2)}`}
                          sub={`Baseline: ${Number(
                            forecastData.summary.baseline_total
                          ).toFixed(2)}`}
                        />
                      </div>
                    ) : (
                      <div className="mt-4 text-sm text-gray-400">
                        Click "Generate Forecast" to see your projection.
                      </div>
                    )}

                    {forecastTimeline.length > 0 ? (
                      <div className="mt-4">
                        <ResponsiveContainer width="100%" height={280}>
                          <LineChart data={forecastTimeline}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                            <XAxis dataKey="week" tick={{ fontSize: 12 }} />
                            <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `${v}`} />
                            <Tooltip formatter={(value) => `${Number(value).toFixed(2)}`} />

                            <Line
                              type="monotone"
                              dataKey="history"
                              name="History"
                              stroke={COLORS[6 % COLORS.length]}
                              strokeWidth={2}
                              dot={{ r: 3 }}
                            />
                            <Line
                              type="monotone"
                              dataKey="baseline"
                              name="Baseline"
                              stroke={COLORS[0 % COLORS.length]}
                              strokeWidth={2}
                              dot={{ r: 3 }}
                            />
                            <Line
                              type="monotone"
                              dataKey="improved"
                              name="Improved"
                              stroke={COLORS[2 % COLORS.length]}
                              strokeWidth={3}
                              dot={{ r: 3 }}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    ) : null}
                  </div>

                  {trends.comparison && (
                    <div
                      className={cn(
                        "rounded-2xl border p-4 shadow-sm",
                        trends.comparison.direction === "up"
                          ? "border-red-200 bg-red-50"
                          : trends.comparison.direction === "down"
                          ? "border-green-200 bg-green-50"
                          : "border-gray-200 bg-white"
                      )}
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-2xl">
                          {trends.comparison.direction === "up"
                            ? "📈"
                            : trends.comparison.direction === "down"
                            ? "📉"
                            : "➡️"}
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
                                  textAnchor={x > cx ? "start" : "end"}
                                  dominantBaseline="central"
                                  style={{ fontSize: "14px", fontWeight: "600" }}
                                >
                                  {`${name} ${(percent * 100).toFixed(0)}%`}
                                </text>
                              );
                            }}
                            labelLine={false}
                          >
                            {Object.entries(trends.spend_by_category).map((_, index) => (
                              <Cell
                                key={`cell-${index}`}
                                fill={COLORS[index % COLORS.length]}
                              />
                            ))}
                          </Pie>
                          <Tooltip formatter={(value) => `${Number(value).toFixed(2)}`} />
                        </PieChart>
                      </ResponsiveContainer>

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
                      <div className="text-lg text-gray-500">No spending data for this period.</div>
                      <div className="text-base text-gray-400 mt-2">
                        Add some receipts to see your trends!
                      </div>
                    </div>
                  )}

                  {chartsData?.spending_over_time?.length > 0 && (
                    <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                      <div className="text-lg font-semibold text-gray-900 mb-4">
                        Spending Over Time
                      </div>
                      <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={chartsData.spending_over_time}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                          <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `${v}`} />
                          <Tooltip formatter={(value) => `${Number(value).toFixed(2)}`} />
                          <Bar dataKey="amount" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}

                  {insights && (
                    <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
                      <div className="text-xl font-semibold text-gray-900">Story</div>
                      <ul className="mt-3 list-disc space-y-2 pl-5 text-base text-gray-700">
                        {(insights.story_insights || []).map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
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

      <div
        className={cn(
          "fixed top-0 right-0 h-full bg-white border-l border-gray-200 shadow-xl transition-transform duration-300 z-50 flex flex-col",
          chatOpen ? "translate-x-0" : "translate-x-full"
        )}
        style={{ width: chatWidth }}
      >
        <div
          className="absolute left-0 top-0 bottom-0 w-2 cursor-ew-resize hover:bg-violet-400 active:bg-violet-500 transition-colors z-10"
          onMouseDown={() => setIsResizing(true)}
        />
        <div className="flex items-center justify-between p-5 border-b border-gray-200">
          <div className="text-xl font-semibold text-gray-900">Chat Assistant</div>
          <button
            onClick={() => setChatOpen(false)}
            className="p-1 hover:bg-gray-100 rounded-lg transition"
            type="button"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5 text-gray-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {chatMessages.length === 0 ? (
            <div className="text-center text-gray-400 text-lg mt-8">
              Ask me anything about your spending!
            </div>
          ) : (
            chatMessages.map((msg, idx) => (
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
              </div>
            ))
          )}
        </div>

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
    </>
  );
}