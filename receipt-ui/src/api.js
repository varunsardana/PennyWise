const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function parseReceipt(file) {
  const fd = new FormData();
  fd.append("file", file);

  const res = await fetch(`${API_BASE}/receipts/parse`, {
    method: "POST",
    body: fd,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Parse failed (${res.status}): ${text}`);
  }
  return await res.json();
}

export async function saveReceipt(payload) {
  const res = await fetch(`${API_BASE}/receipts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Save failed (${res.status}): ${text}`);
  }
  return await res.json();
}

export async function listReceipts() {
  const res = await fetch(`${API_BASE}/receipts`);
  if (!res.ok) throw new Error(`List failed (${res.status})`);
  return await res.json();
}

export async function getInsights(range = "week") {
  const res = await fetch(`${API_BASE}/insights?range=${encodeURIComponent(range)}`);
  if (!res.ok) throw new Error(`Insights failed (${res.status})`);
  return await res.json();
}

export async function getTrends(period = "weekly", startDate = null, endDate = null) {
  let url = `${API_BASE}/trends?period=${encodeURIComponent(period)}`;
  if (startDate) url += `&start_date=${encodeURIComponent(startDate)}`;
  if (endDate) url += `&end_date=${encodeURIComponent(endDate)}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Trends failed (${res.status})`);
  return await res.json();
}

export async function getChartsData(period = "all") {
  const res = await fetch(`${API_BASE}/trends/charts?period=${encodeURIComponent(period)}`);
  if (!res.ok) throw new Error(`Charts failed (${res.status})`);
  return await res.json();
}

export async function deleteReceipt(receiptId) {
  const res = await fetch(`${API_BASE}/receipts/${encodeURIComponent(receiptId)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Delete failed (${res.status})`);
  return await res.json();
}

export async function sendChatMessage(message, conversationHistory = null) {
  const res = await fetch(`${API_BASE}/chatbot/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      conversation_history: conversationHistory,
    }),
  });
  if (!res.ok) throw new Error(`Chat failed (${res.status})`);
  return await res.json();
}

export async function getChatSuggestions() {
  const res = await fetch(`${API_BASE}/chatbot/suggestions`);
  if (!res.ok) throw new Error(`Suggestions failed (${res.status})`);
  return await res.json();
}
