from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from receipt_story.db.tables import Receipt

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _get_date_range(period: str) -> Tuple[datetime, datetime]:
    """
    Calculate start and end dates for the given period.
    Returns (start_date, end_date) as datetime objects.
    """
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == "daily":
        start = today
        end = now
    elif period == "weekly":
        # Start of current week (Monday)
        start = today - timedelta(days=today.weekday())
        end = now
    elif period == "monthly":
        # Start of current month
        start = today.replace(day=1)
        end = now
    elif period == "yearly":
        # Start of current year
        start = today.replace(month=1, day=1)
        end = now
    else:
        # Default to weekly
        start = today - timedelta(days=today.weekday())
        end = now

    return start, end


def _get_previous_date_range(period: str, current_start: datetime) -> Tuple[datetime, datetime]:
    """
    Calculate the previous period's date range for comparison.
    """
    if period == "daily":
        prev_start = current_start - timedelta(days=1)
        prev_end = current_start
    elif period == "weekly":
        prev_start = current_start - timedelta(weeks=1)
        prev_end = current_start
    elif period == "monthly":
        # Previous month
        if current_start.month == 1:
            prev_start = current_start.replace(year=current_start.year - 1, month=12)
        else:
            prev_start = current_start.replace(month=current_start.month - 1)
        prev_end = current_start
    elif period == "yearly":
        # Previous year
        prev_start = current_start.replace(year=current_start.year - 1)
        prev_end = current_start
    else:
        prev_start = current_start - timedelta(weeks=1)
        prev_end = current_start

    return prev_start, prev_end


def _filter_receipts_by_date(receipts: List[Receipt], start: datetime, end: datetime) -> List[Receipt]:
    """
    Filter receipts that fall within the date range.
    Receipt.date is stored as ISO string (YYYY-MM-DD).
    """
    filtered = []
    for r in receipts:
        if not r.date:
            continue
        try:
            receipt_date = datetime.fromisoformat(r.date)
            if start <= receipt_date <= end:
                filtered.append(r)
        except ValueError:
            continue
    return filtered


def _aggregate_by_category(receipts: List[Receipt]) -> Dict[str, float]:
    """Sum spending by category."""
    spend = defaultdict(float)
    for r in receipts:
        spend[r.category] += float(r.total or 0.0)
    return {k: round(v, 2) for k, v in spend.items()}


def _calculate_comparison(
    current_total: float,
    previous_total: float,
    period: str
) -> Optional[Dict]:
    """
    Calculate percentage change between current and previous period.
    """
    if previous_total == 0:
        if current_total == 0:
            return {
                "percent_change": 0.0,
                "direction": "same",
                "message": f"No spending in either period"
            }
        return {
            "percent_change": 100.0,
            "direction": "up",
            "message": f"No spending last {period}, started spending this {period}"
        }

    change = ((current_total - previous_total) / previous_total) * 100
    change = round(change, 1)

    period_label = {
        "daily": "yesterday",
        "weekly": "last week",
        "monthly": "last month",
        "yearly": "last year",
        "custom": "previous period"
    }.get(period, "last period")

    if change > 0:
        return {
            "percent_change": change,
            "direction": "up",
            "message": f"{abs(change)}% more than {period_label}"
        }
    elif change < 0:
        return {
            "percent_change": change,
            "direction": "down",
            "message": f"{abs(change)}% less than {period_label}"
        }
    else:
        return {
            "percent_change": 0.0,
            "direction": "same",
            "message": f"Same as {period_label}"
        }


def compute_trends(
    db: Session,
    period: str = "weekly",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict:
    """
    Main function to compute trends data for the pie chart.

    Args:
        db: Database session
        period: "daily", "weekly", "monthly", "yearly", or "custom"
        start_date: Optional ISO date string for custom range (YYYY-MM-DD)
        end_date: Optional ISO date string for custom range (YYYY-MM-DD)

    Returns:
        Dictionary with spend_by_category, total_spend, comparison, etc.
    """
    # Get all receipts
    all_receipts = db.query(Receipt).all()

    # Calculate date ranges
    if period == "all":
        # All time - no date filtering
        current_receipts = all_receipts
        spend_by_category = _aggregate_by_category(current_receipts)
        total_spend = sum(spend_by_category.values())

        # Find actual date range from receipts
        dates = [r.date for r in all_receipts if r.date]
        if dates:
            period_start = min(dates)
            period_end = max(dates)
        else:
            period_start = datetime.now().date().isoformat()
            period_end = period_start

        return {
            "period": "all",
            "period_start": period_start,
            "period_end": period_end,
            "spend_by_category": spend_by_category,
            "total_spend": round(total_spend, 2),
            "receipt_count": len(current_receipts),
            "comparison": None,
        }
    elif period == "custom" and start_date and end_date:
        current_start = datetime.fromisoformat(start_date)
        current_end = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59)
        # For custom range, no comparison
        prev_start = None
        prev_end = None
    else:
        current_start, current_end = _get_date_range(period)
        prev_start, prev_end = _get_previous_date_range(period, current_start)

    # Filter receipts for current and previous periods
    current_receipts = _filter_receipts_by_date(all_receipts, current_start, current_end)
    previous_receipts = []
    if prev_start and prev_end:
        previous_receipts = _filter_receipts_by_date(all_receipts, prev_start, prev_end)

    # Aggregate spending
    spend_by_category = _aggregate_by_category(current_receipts)
    total_spend = sum(spend_by_category.values())

    previous_total = sum(float(r.total or 0.0) for r in previous_receipts)

    # Calculate comparison (skip for custom range)
    comparison = None
    if period != "custom":
        comparison = _calculate_comparison(total_spend, previous_total, period)

    return {
        "period": period,
        "period_start": current_start.date().isoformat(),
        "period_end": current_end.date().isoformat(),
        "spend_by_category": spend_by_category,
        "total_spend": round(total_spend, 2),
        "receipt_count": len(current_receipts),
        "comparison": comparison,
    }


def compute_charts_data(db: Session, period: str = "all", start_date: str = None, end_date: str = None) -> Dict:
    """
    Compute data for all 4 additional charts.
    Smart grouping based on period:
    - daily: last 30 days, grouped by day
    - weekly: last 12 weeks, grouped by week
    - monthly: last 12 months, grouped by month
    - yearly: all time, grouped by year
    - custom: user-specified range, grouped by day/week/month depending on range size
    - all: all time, grouped by month
    """
    all_receipts = db.query(Receipt).all()
    now = datetime.now()

    # Smart date range and grouping based on period
    if period == "custom" and start_date and end_date:
        filter_start = datetime.fromisoformat(start_date)
        filter_end = datetime.fromisoformat(end_date) + timedelta(days=1)  # Include end date
        range_days = (filter_end - filter_start).days
        # Smart grouping based on range size
        if range_days <= 14:
            date_format = "%b %d"  # Group by day
            parse_format = "%b %d %Y"
        elif range_days <= 90:
            date_format = "W%W %Y"  # Group by week
            parse_format = "W%W %Y"
        else:
            date_format = "%b %Y"  # Group by month
            parse_format = "%b %Y"
        all_receipts = [r for r in all_receipts if r.date and filter_start <= datetime.fromisoformat(r.date) < filter_end]
    elif period == "daily":
        filter_start = now - timedelta(days=30)
        date_format = "%b %d"  # "Jan 11"
        parse_format = "%b %d %Y"
        all_receipts = [r for r in all_receipts if r.date and datetime.fromisoformat(r.date) >= filter_start]
    elif period == "weekly":
        filter_start = now - timedelta(weeks=12)
        date_format = "W%W %Y"  # "W02 2026"
        parse_format = "W%W %Y"
        all_receipts = [r for r in all_receipts if r.date and datetime.fromisoformat(r.date) >= filter_start]
    elif period == "monthly":
        filter_start = now - timedelta(days=365)
        date_format = "%b %Y"  # "Jan 2026"
        parse_format = "%b %Y"
        all_receipts = [r for r in all_receipts if r.date and datetime.fromisoformat(r.date) >= filter_start]
    elif period == "yearly":
        date_format = "%Y"  # "2026"
        parse_format = "%Y"
    else:  # all
        date_format = "%b %Y"  # "Jan 2026"
        parse_format = "%b %Y"

    def get_time_key(dt):
        if period == "weekly":
            return f"W{dt.isocalendar()[1]:02d} {dt.year}"
        return dt.strftime(date_format)

    def parse_time_key(key):
        try:
            if period == "daily":
                return datetime.strptime(key + f" {now.year}", parse_format)
            elif period == "weekly":
                parts = key.split(" ")
                week_num = int(parts[0][1:])
                year = int(parts[1])
                return datetime.strptime(f"{year}-W{week_num:02d}-1", "%Y-W%W-%w")
            else:
                return datetime.strptime(key, parse_format)
        except:
            return datetime.min

    # 1. Spending Over Time - smart grouping
    spending_by_time = defaultdict(float)
    for r in all_receipts:
        if r.date:
            try:
                dt = datetime.fromisoformat(r.date)
                time_key = get_time_key(dt)
                spending_by_time[time_key] += float(r.total or 0)
            except ValueError:
                continue

    spending_over_time = [
        {"date": k, "amount": round(v, 2)}
        for k, v in sorted(spending_by_time.items(), key=lambda x: parse_time_key(x[0]))
    ]

    # 2. Top Merchants
    merchant_data = defaultdict(lambda: {"amount": 0.0, "count": 0})
    for r in all_receipts:
        merchant_data[r.merchant]["amount"] += float(r.total or 0)
        merchant_data[r.merchant]["count"] += 1

    top_merchants = [
        {"merchant": k, "amount": round(v["amount"], 2), "count": v["count"]}
        for k, v in sorted(merchant_data.items(), key=lambda x: x[1]["amount"], reverse=True)
    ][:10]  # Top 10

    # 3. Category Trends - spending by category over time (smart grouping)
    category_by_time = defaultdict(lambda: defaultdict(float))
    all_categories = set()
    for r in all_receipts:
        if r.date:
            try:
                dt = datetime.fromisoformat(r.date)
                time_key = get_time_key(dt)
                category_by_time[time_key][r.category] += float(r.total or 0)
                all_categories.add(r.category)
            except ValueError:
                continue

    category_trends = [
        {
            "date": k,
            "categories": {cat: round(v.get(cat, 0), 2) for cat in all_categories}
        }
        for k, v in sorted(category_by_time.items(), key=lambda x: parse_time_key(x[0]))
    ]

    # 4. Day of Week spending
    day_data = defaultdict(lambda: {"amount": 0.0, "count": 0})
    for r in all_receipts:
        if r.date:
            try:
                dt = datetime.fromisoformat(r.date)
                day_name = DAY_NAMES[dt.weekday()]
                day_data[day_name]["amount"] += float(r.total or 0)
                day_data[day_name]["count"] += 1
            except ValueError:
                continue

    # Ensure all days are present, in order
    day_of_week = [
        {
            "day": day,
            "amount": round(day_data[day]["amount"], 2),
            "count": day_data[day]["count"]
        }
        for day in DAY_NAMES
    ]

    return {
        "spending_over_time": spending_over_time,
        "top_merchants": top_merchants,
        "category_trends": category_trends,
        "day_of_week": day_of_week,
    }
