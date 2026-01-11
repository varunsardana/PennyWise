from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from receipt_story.db.engine import SessionLocal
from receipt_story.services.trends import compute_trends, compute_charts_data
from receipt_story.models.schemas_trends import (
    TrendsResponse, ComparisonData, ChartsDataResponse,
    SpendingOverTimePoint, MerchantSpend, CategoryTrendPoint, DayOfWeekSpend
)

router = APIRouter(prefix="/trends", tags=["trends"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=TrendsResponse)
def get_trends(
    period: str = Query("weekly", description="Time period: daily, weekly, monthly, yearly, or custom"),
    start_date: Optional[str] = Query(None, description="Start date for custom range (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date for custom range (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get spending trends for pie chart visualization.

    - **period**: "daily", "weekly", "monthly", "yearly", or "custom"
    - **start_date**: Required for custom period (YYYY-MM-DD)
    - **end_date**: Required for custom period (YYYY-MM-DD)

    Returns spend by category, total spend, and comparison to previous period.
    """
    # Validate period
    if period not in ["daily", "weekly", "monthly", "yearly", "all", "custom"]:
        period = "weekly"

    # If custom but missing dates, fall back to weekly
    if period == "custom" and (not start_date or not end_date):
        period = "weekly"

    data = compute_trends(db, period=period, start_date=start_date, end_date=end_date)

    comparison = None
    if data.get("comparison"):
        comparison = ComparisonData(**data["comparison"])

    return TrendsResponse(
        period=data["period"],
        period_start=data["period_start"],
        period_end=data["period_end"],
        spend_by_category=data["spend_by_category"],
        total_spend=data["total_spend"],
        receipt_count=data["receipt_count"],
        comparison=comparison,
    )


@router.get("/charts", response_model=ChartsDataResponse)
def get_charts_data(
    period: str = Query("all", description="Time period: daily, weekly, monthly, yearly, custom, or all"),
    start_date: Optional[str] = Query(None, description="Start date for custom range (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date for custom range (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get data for additional charts:
    - Spending over time (monthly)
    - Top merchants
    - Category trends over time
    - Day of week spending
    """
    if period not in ["daily", "weekly", "monthly", "yearly", "all", "custom"]:
        period = "all"

    # If custom but missing dates, fall back to all
    if period == "custom" and (not start_date or not end_date):
        period = "all"

    data = compute_charts_data(db, period=period, start_date=start_date, end_date=end_date)

    return ChartsDataResponse(
        spending_over_time=[SpendingOverTimePoint(**p) for p in data["spending_over_time"]],
        top_merchants=[MerchantSpend(**m) for m in data["top_merchants"]],
        category_trends=[CategoryTrendPoint(**c) for c in data["category_trends"]],
        day_of_week=[DayOfWeekSpend(**d) for d in data["day_of_week"]],
    )
