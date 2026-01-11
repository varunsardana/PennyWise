from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta

from receipt_story.db.engine import SessionLocal  # match how routes_receipts does it

router = APIRouter(prefix="/advisor", tags=["advisor"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _weighted_forecast(history, horizon: int):
    """
    history: list[float] weekly totals (oldest -> newest)
    returns list[float] length horizon
    """
    if len(history) < 3:
        # fallback: repeat last known value
        last = history[-1] if history else 0.0
        return [last for _ in range(horizon)]

    a, b, c = history[-3], history[-2], history[-1]
    preds = []
    for _ in range(horizon):
        nxt = 0.2 * a + 0.3 * b + 0.5 * c
        preds.append(round(float(nxt), 2))
        a, b, c = b, c, nxt
    return preds

@router.get("/forecast")
def forecast(horizon: int = 12, db: Session = Depends(get_db)):
    """
    Returns:
    - history weekly totals
    - baseline forecast for next N weeks
    - improved forecast using a simple plan (reduce top overspend category)
    """

    # 1) Weekly totals (history)
    weekly = db.execute(text("""
        SELECT strftime('%Y-%W', date) AS wk,
               ROUND(SUM(total), 2) AS total
        FROM receipts
        WHERE date IS NOT NULL AND date != ''
        GROUP BY wk
        ORDER BY wk;
    """)).mappings().all()

    history = [{"week": r["wk"], "total": float(r["total"] or 0.0)} for r in weekly]
    history_totals = [h["total"] for h in history]

    # 2) Find last 30 days category shares (to decide plan target)
    # SQLite date filtering: use created_at fallback if needed
    cat_rows = db.execute(text("""
        SELECT category,
               ROUND(SUM(total), 2) AS spend
        FROM receipts
        WHERE date IS NOT NULL AND date != ''
          AND date >= date('now', '-30 day')
        GROUP BY category
        ORDER BY spend DESC;
    """)).mappings().all()

    cat_spend = [{"category": r["category"], "spend": float(r["spend"] or 0.0)} for r in cat_rows]
    total_30d = sum(r["spend"] for r in cat_spend) or 0.0

    top_category = cat_spend[0]["category"] if cat_spend else "Other"
    top_spend = cat_spend[0]["spend"] if cat_spend else 0.0
    top_share = (top_spend / total_30d) if total_30d > 0 else 0.0

    # 3) Baseline forecast
    baseline_vals = _weighted_forecast(history_totals, horizon=horizon)

    # 4) Improved forecast: reduce top category by a fixed % (simple “plan”)
    reduction_percent = 0.20  # 20% cut to top category
    savings_percent = top_share * reduction_percent  # overall savings rate
    improved_vals = [round(v * (1.0 - savings_percent), 2) for v in baseline_vals]

    # 5) Build future week labels (just sequential W1..Wn)
    future = [{"week": f"F+{i+1}", "total": baseline_vals[i]} for i in range(horizon)]
    improved = [{"week": f"F+{i+1}", "total": improved_vals[i]} for i in range(horizon)]

    baseline_total = round(sum(baseline_vals), 2)
    improved_total = round(sum(improved_vals), 2)
    savings = round(baseline_total - improved_total, 2)

    return {
        "history": history,
        "baseline": future,
        "improved": improved,
        "plan": {
            "top_category": top_category,
            "reduction_percent": int(reduction_percent * 100),
            "top_category_share_30d": round(top_share, 3),
            "estimated_overall_savings_percent": round(savings_percent, 3),
        },
        "summary": {
            "baseline_total": baseline_total,
            "improved_total": improved_total,
            "savings": savings,
        },
    }
